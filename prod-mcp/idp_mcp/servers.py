"""Les 4 serveurs MCP de production. Contrats IDENTIQUES au kit (parité testée).

Catalogue EN LECTURE SEULE : aucun outil ne modifie ni ne supprime de données.
Si un jour vous ajoutez une écriture, elle DOIT passer par un HITL (interrupt)
côté runtime DeepAgents — jamais une écriture silencieuse ici.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import backends, config
from .sqlguard import SqlNotAllowed, ensure_readonly_select

S = config.SCHEMA


def _documents() -> FastMCP:
    mcp = FastMCP("documents", host=config.HOST, port=config.PORTS["documents"])

    @mcp.tool()
    async def search_documents(query: str) -> list[dict]:
        """Cherche dans le corpus documentaire (factures, contrats, courriers)."""
        sql = (
            f"SELECT * FROM {S.documents_table} "
            f"WHERE {S.documents_text} ILIKE $1 OR {S.documents_title} ILIKE $1 "
            f"LIMIT {config.ROW_CAP}"
        )
        return await backends.pg_fetch(sql, f"%{query}%")

    @mcp.tool()
    async def get_document(doc_id: str) -> dict | None:
        """Récupère un document complet par identifiant (ex INV-2026-0042)."""
        sql = f"SELECT * FROM {S.documents_table} WHERE {S.documents_id} = $1 LIMIT 1"
        rows = await backends.pg_fetch(sql, doc_id, cap=1)
        return rows[0] if rows else None

    return mcp


def _relational() -> FastMCP:
    mcp = FastMCP("relational", host=config.HOST, port=config.PORTS["relational"])

    @mcp.tool()
    async def sql_query(sql: str) -> list[dict]:
        """Exécute un SELECT en lecture seule sur la base relationnelle (documents, suppliers, jobs)."""
        try:
            safe = ensure_readonly_select(sql)
        except SqlNotAllowed as e:
            return [{"error": f"requête refusée : {e}"}]
        return await backends.pg_fetch(safe)

    @mcp.tool()
    async def lookup_supplier(name: str) -> dict | None:
        """Recherche un fournisseur (statut, conditions de paiement)."""
        sql = f"SELECT * FROM {S.suppliers_table} WHERE {S.suppliers_name} ILIKE $1 LIMIT 1"
        rows = await backends.pg_fetch(sql, f"%{name}%", cap=1)
        return rows[0] if rows else None

    @mcp.tool()
    async def list_jobs(status: str | None = None) -> list[dict]:
        """Liste les jobs d'ingestion, filtrable par statut (done/pending/error)."""
        if status:
            sql = f"SELECT * FROM {S.jobs_table} WHERE {S.jobs_status} = $1 LIMIT {config.ROW_CAP}"
            return await backends.pg_fetch(sql, status)
        return await backends.pg_fetch(f"SELECT * FROM {S.jobs_table} LIMIT {config.ROW_CAP}")

    return mcp


def _vector() -> FastMCP:
    mcp = FastMCP("vector", host=config.HOST, port=config.PORTS["vector"])

    @mcp.tool()
    async def vector_search(query: str, top_k: int = 3) -> list[dict]:
        """Recherche sémantique : renvoie les passages les plus proches du texte."""
        vec = await backends.embed(query)
        client = backends.qdrant_client()
        res = await client.search(
            collection_name=config.QDRANT_COLLECTION,
            query_vector=vec, limit=top_k, with_payload=True,
        )
        return [{"id": str(p.id), "score": float(p.score), **(p.payload or {})} for p in res]

    return mcp


def _graph() -> FastMCP:
    mcp = FastMCP("graph", host=config.HOST, port=config.PORTS["graph"])

    @mcp.tool()
    def find_entity(name: str) -> list[dict]:
        """Trouve des entités du graphe de connaissances par nom."""
        db = backends.arango_db()
        aql = (
            f"FOR e IN {S.entities_coll} "
            f"FILTER LOWER(e.{S.entity_name}) LIKE LOWER(@q) "
            f"LIMIT {config.ROW_CAP} RETURN e"
        )
        return list(db.aql.execute(aql, bind_vars={"q": f"%{name}%"}))

    @mcp.tool()
    def graph_neighbors(entity_id: str) -> dict:
        """Voisinage direct d'une entité (relations entrantes/sortantes)."""
        db = backends.arango_db()
        aql = (
            f"FOR v, e IN 1..1 ANY @start {S.relations_coll} "
            f"RETURN {{rel: e.rel, direction: (e._from == @start ? 'out' : 'in'), "
            f"node: v._id, name: v.{S.entity_name}}}"
        )
        edges = list(db.aql.execute(aql, bind_vars={"start": entity_id}))
        return {"entity": entity_id, "edges": edges}

    @mcp.tool()
    def graph_path(src: str, dst: str) -> list[str] | dict:
        """Plus court chemin entre deux entités du graphe."""
        db = backends.arango_db()
        aql = (
            f"FOR v IN OUTBOUND SHORTEST_PATH @src TO @dst {S.relations_coll} "
            f"RETURN v._id"
        )
        path = list(db.aql.execute(aql, bind_vars={"src": src, "dst": dst}))
        return path if path else {"error": "aucun chemin trouvé"}

    return mcp


FACTORIES = {
    "documents": _documents, "relational": _relational,
    "vector": _vector, "graph": _graph,
}


def run(name: str) -> None:
    if name not in FACTORIES:
        raise SystemExit(f"Serveur inconnu : {name}. Choix : {list(FACTORIES)}")
    FACTORIES[name]().run(transport="streamable-http")
