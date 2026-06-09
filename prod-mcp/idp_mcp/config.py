"""Configuration par variables d'environnement + mapping de schéma.

Sécurité : préférez l'auth par rôle (IRSA/Workload Identity) et un RÔLE POSTGRES
EN LECTURE SEULE. Aucun secret en clair dans le code. L'égress doit être restreint.
"""
from __future__ import annotations

import os
import re as _re
from dataclasses import dataclass

HOST = os.getenv("MCP_HOST", "127.0.0.1")
PORTS = {"documents": 9101, "relational": 9102, "vector": 9103, "graph": 9104}

# --- PostgreSQL (relational + documents) -------------------------------------
# Ex : postgresql://idp_ro@pg-host:5432/idp  (idp_ro = rôle GRANT SELECT uniquement)
PG_DSN = os.getenv("IDP_PG_DSN", "")
PG_STATEMENT_TIMEOUT_S = float(os.getenv("IDP_PG_STATEMENT_TIMEOUT_S", "5"))
ROW_CAP = int(os.getenv("IDP_ROW_CAP", "200"))   # plafond de lignes renvoyées

# --- ArangoDB (graph) --------------------------------------------------------
ARANGO_URL = os.getenv("IDP_ARANGO_URL", "http://localhost:8529")
ARANGO_DB = os.getenv("IDP_ARANGO_DB", "idp")
ARANGO_USER = os.getenv("IDP_ARANGO_USER", "")
ARANGO_PASSWORD = os.getenv("IDP_ARANGO_PASSWORD", "")

# --- Qdrant (vector) ---------------------------------------------------------
QDRANT_URL = os.getenv("IDP_QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("IDP_QDRANT_API_KEY", "") or None
QDRANT_COLLECTION = os.getenv("IDP_QDRANT_COLLECTION", "documents")

# --- Embedding ---------------------------------------------------------------
# ⚠ DOIT correspondre EXACTEMENT au modèle ayant indexé Qdrant (même modèle, même
#    dimension), sinon la similarité est du bruit. 'http' = endpoint approuvé.
EMBEDDING_PROVIDER = os.getenv("IDP_EMBEDDING_PROVIDER", "")     # http | fastembed
EMBEDDING_ENDPOINT = os.getenv("IDP_EMBEDDING_ENDPOINT", "")
EMBEDDING_MODEL = os.getenv("IDP_EMBEDDING_MODEL", "")


@dataclass(frozen=True)
class Schema:
    """Mappez ces noms à votre schéma réel (défauts = domaine du kit)."""
    documents_table: str = os.getenv("IDP_T_DOCUMENTS", "documents")
    documents_id: str = os.getenv("IDP_C_DOC_ID", "doc_id")
    documents_text: str = os.getenv("IDP_C_DOC_TEXT", "content")
    documents_title: str = os.getenv("IDP_C_DOC_TITLE", "title")
    suppliers_table: str = os.getenv("IDP_T_SUPPLIERS", "suppliers")
    suppliers_name: str = os.getenv("IDP_C_SUPPLIER_NAME", "name")
    jobs_table: str = os.getenv("IDP_T_JOBS", "jobs")
    jobs_status: str = os.getenv("IDP_C_JOB_STATUS", "status")
    entities_coll: str = os.getenv("IDP_COLL_ENTITIES", "entities")
    relations_coll: str = os.getenv("IDP_COLL_RELATIONS", "relations")
    entity_name: str = os.getenv("IDP_F_ENTITY_NAME", "name")


SCHEMA = Schema()

# Les identifiants (tables/colonnes/collections) sont interpolés dans SQL/AQL :
# ils viennent de l'OPÉRATEUR (env), jamais de l'agent. On les valide quand même.
_IDENT = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
for _label, _val in vars(SCHEMA).items():
    if not _IDENT.match(_val):
        raise ValueError(f"Identifiant SQL/AQL invalide pour {_label}: {_val!r}")
