"""Source RELATIONNELLE mock — vrai SQLite en mémoire.

Comportement SQL réel (jointures, agrégats…), zéro service séparé. En prod, on
remplace ceci par le vrai PostgreSQL : le contrat MCP (sql_query, lookup_supplier…)
reste identique, donc aucun skill à retoucher.
"""
from __future__ import annotations

import sqlite3
from typing import Any


class RelationalSource:
    def __init__(self, data: dict[str, Any]) -> None:
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._seed(data)

    def _seed(self, data: dict[str, Any]) -> None:
        cur = self.db.cursor()
        cur.executescript(
            """
            CREATE TABLE documents(id TEXT PRIMARY KEY, type TEXT, issuer TEXT,
                date TEXT, amount_ht REAL, vat REAL, amount_ttc REAL, currency TEXT, po_number TEXT);
            CREATE TABLE suppliers(name TEXT PRIMARY KEY, status TEXT, payment_terms TEXT);
            CREATE TABLE jobs(job_id TEXT PRIMARY KEY, doc_id TEXT, stage TEXT, status TEXT);
            """
        )
        for d in data.get("documents", []):
            cur.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
                (d["id"], d.get("type"), d.get("issuer"), d.get("date"),
                 d.get("amount_ht"), d.get("vat"), d.get("amount_ttc"),
                 d.get("currency"), d.get("po_number")),
            )
        for e in data.get("entities", []):
            if e.get("type") == "supplier":
                cur.execute("INSERT OR IGNORE INTO suppliers VALUES(?,?,?)",
                            (e["name"], e.get("status"), e.get("payment_terms")))
        for j in data.get("relational", {}).get("jobs", []):
            cur.execute("INSERT INTO jobs VALUES(?,?,?,?)",
                        (j["job_id"], j["doc_id"], j["stage"], j["status"]))
        self.db.commit()

    # --- API exposée via MCP --------------------------------------------
    def run_sql(self, sql: str) -> list[dict]:
        """Exécute un SELECT en lecture seule et renvoie les lignes."""
        if not sql.strip().lower().startswith("select"):
            raise ValueError("Lecture seule : seuls les SELECT sont autorisés.")
        cur = self.db.execute(sql)
        return [dict(r) for r in cur.fetchall()]

    def lookup_supplier(self, name: str) -> dict | None:
        cur = self.db.execute(
            "SELECT * FROM suppliers WHERE lower(name) LIKE ?", (f"%{name.lower()}%",))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_jobs(self, status: str | None = None) -> list[dict]:
        if status:
            cur = self.db.execute("SELECT * FROM jobs WHERE status=?", (status,))
        else:
            cur = self.db.execute("SELECT * FROM jobs")
        return [dict(r) for r in cur.fetchall()]

    def document_meta(self, doc_id: str) -> dict | None:
        cur = self.db.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
        row = cur.fetchone()
        return dict(row) if row else None
