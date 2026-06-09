"""Quatre serveurs MCP RÉELS, un par source, devant la couche mockée.

Les contrats (noms d'outils + schémas) sont identiques à ce qu'on exposerait en
prod. Seuls les moteurs derrière sont mockés. Un agent voit donc exactement la
même topologie « tools = MCP » qu'en production.

Lancement :
    python -m mcp_servers documents   # un serveur (bloquant)
    python -m mcp_servers all         # les quatre (sous-process)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from mock_sources import get_graph, get_relational, get_store, get_vector

HOST = os.getenv("MCP_HOST", "127.0.0.1")

# nom -> (port, fabrique de serveur)
PORTS = {"documents": 9101, "relational": 9102, "vector": 9103, "graph": 9104}


def _documents() -> FastMCP:
    mcp = FastMCP("documents", host=HOST, port=PORTS["documents"])

    @mcp.tool()
    def search_documents(query: str) -> list[dict]:
        """Cherche dans le corpus documentaire (factures, contrats, courriers)."""
        return get_store().search(query)

    @mcp.tool()
    def get_document(doc_id: str) -> dict | None:
        """Récupère un document complet par identifiant (ex INV-2026-0042)."""
        return get_store().get(doc_id)

    return mcp


def _relational() -> FastMCP:
    mcp = FastMCP("relational", host=HOST, port=PORTS["relational"])

    @mcp.tool()
    def sql_query(sql: str) -> list[dict]:
        """Exécute un SELECT en lecture seule sur la base relationnelle (documents, suppliers, jobs)."""
        return get_relational().run_sql(sql)

    @mcp.tool()
    def lookup_supplier(name: str) -> dict | None:
        """Recherche un fournisseur (statut, conditions de paiement)."""
        return get_relational().lookup_supplier(name)

    @mcp.tool()
    def list_jobs(status: str | None = None) -> list[dict]:
        """Liste les jobs d'ingestion, filtrable par statut (done/pending/error)."""
        return get_relational().list_jobs(status)

    return mcp


def _vector() -> FastMCP:
    mcp = FastMCP("vector", host=HOST, port=PORTS["vector"])

    @mcp.tool()
    def vector_search(query: str, top_k: int = 3) -> list[dict]:
        """Recherche sémantique : renvoie les passages les plus proches du texte."""
        return get_vector().search(query, top_k)

    return mcp


def _graph() -> FastMCP:
    mcp = FastMCP("graph", host=HOST, port=PORTS["graph"])

    @mcp.tool()
    def find_entity(name: str) -> list[dict]:
        """Trouve des entités du graphe de connaissances par nom."""
        return get_graph().find_entity(name)

    @mcp.tool()
    def graph_neighbors(entity_id: str) -> dict:
        """Voisinage direct d'une entité (relations entrantes/sortantes)."""
        return get_graph().neighbors(entity_id)

    @mcp.tool()
    def graph_path(src: str, dst: str) -> list[str] | dict:
        """Plus court chemin entre deux entités du graphe."""
        return get_graph().path(src, dst)

    return mcp


FACTORIES = {"documents": _documents, "relational": _relational,
             "vector": _vector, "graph": _graph}


def run(name: str) -> None:
    if name not in FACTORIES:
        raise SystemExit(f"Serveur inconnu : {name}. Choix : {list(FACTORIES)}")
    FACTORIES[name]().run(transport="streamable-http")


# --- extension : serveurs générés (ne pas modifier) -------------------------
try:
    from .servers_generated import GENERATED_PORTS, GENERATED_FACTORIES
    PORTS.update(GENERATED_PORTS)
    FACTORIES.update(GENERATED_FACTORIES)
except ImportError:
    pass
