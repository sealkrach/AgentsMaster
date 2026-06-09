"""Teste la garde SQL lecture-seule (dépendance-zéro)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from idp_mcp.sqlguard import SqlNotAllowed, ensure_readonly_select  # noqa: E402

ALLOW = [
    "SELECT 1",
    "select * from jobs where status = $1",
    "WITH x AS (SELECT 1 AS a) SELECT a FROM x",
    "  SELECT count(*) FROM documents -- commentaire\n",
]
DENY = [
    "",
    "INSERT INTO jobs VALUES (1)",
    "UPDATE jobs SET status='done'",
    "DROP TABLE jobs",
    "SELECT 1; DROP TABLE jobs",
    "SELECT * INTO copie FROM jobs",
    "TRUNCATE jobs",
    "SET default_transaction_read_only = off",
]


def main() -> int:
    bad = 0
    for q in ALLOW:
        try:
            ensure_readonly_select(q)
        except SqlNotAllowed as e:
            bad += 1
            print(f"❌ devrait PASSER mais refusé : {q!r} ({e})")
    for q in DENY:
        try:
            ensure_readonly_select(q)
            bad += 1
            print(f"❌ devrait être REFUSÉ mais accepté : {q!r}")
        except SqlNotAllowed:
            pass
    if bad == 0:
        print(f"✅ GARDE SQL OK — {len(ALLOW)} acceptés, {len(DENY)} refusés comme prévu.")
        return 0
    print(f"\n{bad} cas en échec.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
