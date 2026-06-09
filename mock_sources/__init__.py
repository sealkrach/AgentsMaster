"""Couche de sources mockées du lab.

Charge data/synthetic/landscape.json une fois et expose quatre sources avec un
comportement RÉEL mais zéro service séparé :
  - get_relational()  → SQLite (vrai SQL)
  - get_vector()      → ranking cosinus (hors-ligne)
  - get_graph()       → networkx (vraies traversées)
  - get_store()       → corpus documentaire

Le contrat (ces accesseurs + les outils MCP devant) est identique à la prod ;
seuls les moteurs derrière changent quand on graduera vers Postgres/Qdrant/Arango.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .graph import GraphSource
from .relational import RelationalSource
from .store import DocumentStore
from .vector import VectorSource

_LANDSCAPE = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "landscape.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_LANDSCAPE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def get_relational() -> RelationalSource:
    return RelationalSource(_data())


@lru_cache(maxsize=1)
def get_vector() -> VectorSource:
    return VectorSource(_data())


@lru_cache(maxsize=1)
def get_graph() -> GraphSource:
    return GraphSource(_data())


@lru_cache(maxsize=1)
def get_store() -> DocumentStore:
    return DocumentStore(_data())
