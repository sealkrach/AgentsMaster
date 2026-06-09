"""Assemblage de l'agent du lab selon la topologie choisie.

  - runtime = commodity (DeepAgents/LangGraph), non réinventé ;
  - outils = MCP (vrais serveurs) ou in-proc, contrat identique ;
  - topologie = single | supervisor | swarm (LAB_TOPOLOGY) ;
  - HITL = interrupt_on + checkpointer ; progressive disclosure des skills.
"""
from __future__ import annotations

from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

from . import config, topologies
from .mcp_tools import load_tools


async def _make_checkpointer():
    """MemorySaver par défaut ; AsyncSqliteSaver si CHECKPOINT_DB est défini."""
    if not config.CHECKPOINT_DB:
        return MemorySaver()
    try:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        conn = await aiosqlite.connect(config.CHECKPOINT_DB)
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        return saver
    except ImportError:
        import warnings
        warnings.warn(
            "CHECKPOINT_DB défini mais aiosqlite/langgraph-checkpoint-sqlite manquants. "
            "Exécutez : pip install aiosqlite langgraph-checkpoint-sqlite. "
            "Fallback sur MemorySaver.",
            stacklevel=2,
        )
        return MemorySaver()

SYSTEM_PROMPT = (
    "Tu es l'agent du bac à sable de l'agentathon. Tu aides à traiter des documents "
    "métier (factures, contrats) via tes skills et tes outils (relationnel, vecteur, "
    "graphe, corpus). Données SYNTHÉTIQUES uniquement. Quand une tâche correspond à un "
    "skill, lis-le et suis-le. Avant toute écriture, demande validation."
)

_AGENT = None
RUNTIME_INFO: dict = {}  # peuplé au build, exposé par /info (outils connectés)


async def build_agent():
    """Construit (une fois) l'agent du lab selon LAB_TOPOLOGY."""
    global _AGENT
    if _AGENT is not None:
        return _AGENT
    model = config.require_model()
    tools = await load_tools()
    RUNTIME_INFO["tools"] = [
        {"name": getattr(t, "name", "?"),
         "description": (getattr(t, "description", "") or "")[:160]}
        for t in tools
    ]
    # virtual_mode=False : sémantique disque (skills lus depuis le repo). L'isolation
    # réelle vient du sandbox pod OpenShift (montages read-only, UID non-root), pas d'ici.
    backend = FilesystemBackend(root_dir=str(config.REPO_ROOT), virtual_mode=False)
    checkpointer = await _make_checkpointer()
    _AGENT = topologies.build(
        config.LAB_TOPOLOGY, model=model, tools=tools,
        skills_dir=str(config.SKILLS_DIR), backend=backend,
        checkpointer=checkpointer, interrupt_on=config.INTERRUPT_ON,
        system_prompt=SYSTEM_PROMPT,
    )
    return _AGENT
