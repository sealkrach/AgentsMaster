"""Chargement des outils du runtime.

Deux modes (même contrat dans les deux) :
  - "mcp"    : charge depuis les VRAIS serveurs MCP via MultiServerMCPClient
               (reproduit fidèlement la topologie « tools = MCP » de la prod).
  - "inproc" : outils locaux (fallback laptop/CI, zéro serveur à lancer).
"""
from __future__ import annotations

from . import config


async def load_tools() -> list:
    if config.MCP_MODE == "inproc":
        from .tools import INPROC_TOOLS
        return list(INPROC_TOOLS)

    from langchain_mcp_adapters.client import MultiServerMCPClient
    client = MultiServerMCPClient({
        name: {"url": url, "transport": "streamable_http"}
        for name, url in config.MCP_SERVERS.items()
    })
    return await client.get_tools()


def by_names(tools: list, names: set[str]) -> list:
    """Sous-ensemble d'outils par nom (pour les subagents)."""
    return [t for t in tools if t.name in names]
