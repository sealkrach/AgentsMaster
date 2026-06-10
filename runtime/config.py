"""Configuration du runtime du lab agentathon."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Modèle (provider:model). Pointez vers votre endpoint approuvé. ---------
LAB_MODEL = os.getenv("LAB_MODEL", "").strip()

# --- Skills & données -------------------------------------------------------
SKILLS_DIR = REPO_ROOT / "skills"

# --- Identité ---------------------------------------------------------------
TEAM_NAME = os.getenv("TEAM_NAME", "lab")
LAB_TITLE = os.getenv("LAB_TITLE", "Agentathon Lab")

# --- Topologie d'agent : single | supervisor | swarm ------------------------
LAB_TOPOLOGY = os.getenv("LAB_TOPOLOGY", "single").strip().lower()

# --- Couche outils : "mcp" (vrais serveurs MCP) ou "inproc" (fallback laptop)
MCP_MODE = os.getenv("MCP_MODE", "mcp").strip().lower()
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
# URLs des serveurs MCP (surchargées par env en OpenShift via les Services).
MCP_SERVERS = {
    "documents":  os.getenv("MCP_DOCUMENTS_URL",  f"http://{MCP_HOST}:9101/mcp"),
    "relational": os.getenv("MCP_RELATIONAL_URL", f"http://{MCP_HOST}:9102/mcp"),
    "vector":     os.getenv("MCP_VECTOR_URL",     f"http://{MCP_HOST}:9103/mcp"),
    "graph":      os.getenv("MCP_GRAPH_URL",      f"http://{MCP_HOST}:9104/mcp"),
}

# --- Checkpointer persistant (vide = MemorySaver en mémoire) ----------------
# Exemples : CHECKPOINT_DB=checkpoints.db  ou  CHECKPOINT_DB=/data/lab.db
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", "").strip()

# --- Garde-fous Human-in-the-loop -------------------------------------------
INTERRUPT_ON = {
    "write_file": os.getenv("HITL_WRITE", "true").lower() == "true",
    "edit_file": os.getenv("HITL_EDIT", "true").lower() == "true",
    "read_file": False,
}


# --- extension : serveurs MCP générés (ne pas modifier) ---------------------
try:
    from .config_generated import GENERATED_MCP_SERVERS
    MCP_SERVERS.update(GENERATED_MCP_SERVERS)
except ImportError:
    pass


# --- S1 : Registre PostgreSQL + pgvector ------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lab:lab@localhost:5432/agentathon",
)
REGISTRY_ENABLED: bool = bool(os.getenv("DATABASE_URL"))

# Embeddings (OpenAI text-embedding-3-small par défaut, 1536 dims)
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "")


def require_model() -> str:
    if not LAB_MODEL:
        raise RuntimeError(
            "LAB_MODEL n'est pas défini. Copiez .env.example en .env et renseignez "
            "votre modèle, ex: LAB_MODEL=anthropic:claude-sonnet-4-5"
        )
    return LAB_MODEL
