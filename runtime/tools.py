"""Outils IN-PROC du lab (fallback laptop/CI).

Mêmes noms et mêmes contrats que les serveurs MCP — pour qu'un skill se comporte
identiquement, qu'on soit en mode `mcp` (vrais serveurs) ou `inproc`. Tout passe
par la couche mock_sources (SQLite / cosinus / networkx / corpus).
"""
from __future__ import annotations

from langchain_core.tools import tool

from mock_sources import get_graph, get_relational, get_store, get_vector


@tool
def search_documents(query: str) -> list:
    """Cherche dans le corpus documentaire (factures, contrats, courriers)."""
    return get_store().search(query)


@tool
def get_document(doc_id: str) -> dict | None:
    """Récupère un document complet par identifiant (ex INV-2026-0042)."""
    return get_store().get(doc_id)


@tool
def sql_query(sql: str) -> list:
    """Exécute un SELECT en lecture seule (tables documents, suppliers, jobs)."""
    return get_relational().run_sql(sql)


@tool
def lookup_supplier(name: str) -> dict | None:
    """Recherche un fournisseur (statut, conditions de paiement)."""
    return get_relational().lookup_supplier(name)


@tool
def list_jobs(status: str | None = None) -> list:
    """Liste les jobs d'ingestion, filtrable par statut (done/pending/error)."""
    return get_relational().list_jobs(status)


@tool
def vector_search(query: str, top_k: int = 3) -> list:
    """Recherche sémantique : passages les plus proches du texte."""
    return get_vector().search(query, top_k)


@tool
def find_entity(name: str) -> list:
    """Trouve des entités du graphe de connaissances par nom."""
    return get_graph().find_entity(name)


@tool
def graph_neighbors(entity_id: str) -> dict:
    """Voisinage direct d'une entité (relations entrantes/sortantes)."""
    return get_graph().neighbors(entity_id)


@tool
def graph_path(src: str, dst: str) -> list | dict:
    """Plus court chemin entre deux entités du graphe."""
    return get_graph().path(src, dst)


INPROC_TOOLS = [search_documents, get_document, sql_query, lookup_supplier,
                list_jobs, vector_search, find_entity, graph_neighbors, graph_path]

# --- extension : outils générés (ne pas modifier) ---------------------------
try:
    from .tools_generated import GENERATED_INPROC_TOOLS
    INPROC_TOOLS.extend(GENERATED_INPROC_TOOLS)
except ImportError:
    pass
