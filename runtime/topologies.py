"""Trois topologies d'agents, sur le même socle DeepAgents/LangGraph.

  - single     : un agent unique, tous les outils + skills (le défaut).
  - supervisor : un agent chef qui délègue à des subagents spécialisés
                 (retriever = contexte/graphe/vecteur ; decider = relationnel/décision).
  - swarm      : deux agents pairs qui se passent la main via des outils de handoff.

Sélection par la variable LAB_TOPOLOGY. Les trois consomment les mêmes outils
(MCP ou in-proc) et les mêmes skills — on ne change que l'orchestration.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from deepagents import create_deep_agent
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command

from .mcp_tools import by_names

RETRIEVAL = {"vector_search", "find_entity", "graph_neighbors", "graph_path",
             "search_documents", "get_document"}
RELATIONAL = {"lookup_supplier", "sql_query", "list_jobs"}


def build(name, *, model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt):
    if name == "supervisor":
        return _supervisor(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt)
    if name == "swarm":
        return _swarm(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt)
    return _single(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt)


def _single(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt):
    return create_deep_agent(
        model=model, tools=tools, skills=[skills_dir], backend=backend,
        system_prompt=system_prompt, interrupt_on=interrupt_on, checkpointer=checkpointer,
    )


def _supervisor(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt):
    retriever = {
        "name": "retriever",
        "description": "Récupère le contexte : documents, recherche sémantique, graphe de connaissances.",
        "system_prompt": "Tu récupères le contexte pertinent via tes outils (vecteur, graphe, corpus) et le renvoies de façon structurée.",
        "tools": by_names(tools, RETRIEVAL),
        "skills": [skills_dir],
    }
    decider = {
        "name": "decider",
        "description": "Vérifie les faits relationnels (fournisseur, jobs, SQL) et formule une décision motivée.",
        "system_prompt": "Tu vérifies les faits relationnels et statues avec une justification citant les identifiants.",
        "tools": by_names(tools, RELATIONAL),
        "skills": [skills_dir],
    }
    sup_prompt = (system_prompt or "") + (
        "\nTu es le chef d'orchestre. Délègue la récupération de contexte au "
        "subagent 'retriever' et la vérification/décision au subagent 'decider', "
        "puis synthétise."
    )
    return create_deep_agent(
        model=model, tools=[], skills=[skills_dir], backend=backend,
        subagents=[retriever, decider], system_prompt=sup_prompt,
        interrupt_on=interrupt_on, checkpointer=checkpointer,
    )


def _handoff_tool(to: str):
    @tool(f"handoff_to_{to}")
    def _h(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        """Transfère la conversation à l'agent pair indiqué quand il est plus compétent."""
        return Command(
            goto=to, graph=Command.PARENT,
            update={"active": to,
                    "messages": [ToolMessage(content=f"Transféré à {to}.", tool_call_id=tool_call_id)]},
        )
    return _h


class _SwarmState(TypedDict):
    messages: Annotated[list, add_messages]
    active: str


def _swarm(model, tools, skills_dir, backend, checkpointer, interrupt_on, system_prompt):
    triage = create_deep_agent(
        model=model, backend=backend, skills=[skills_dir],
        interrupt_on=interrupt_on,
        tools=by_names(tools, RELATIONAL) + [_handoff_tool("research")],
        system_prompt=(
            "Tu es l'agent de triage : questions relationnelles (fournisseurs, jobs, SQL). "
            "Si la tâche nécessite du contexte documentaire, sémantique ou de graphe, "
            "passe la main UNE SEULE FOIS via handoff_to_research. "
            "Si research te repasse la main avec le contexte réuni, formule la réponse "
            "finale directement — ne repasse JAMAIS la main une deuxième fois. "
            "Avant toute écriture de fichier, demande validation."
        ),
        name="triage",
    )
    research = create_deep_agent(
        model=model, backend=backend, skills=[skills_dir],
        interrupt_on=interrupt_on,
        tools=by_names(tools, RETRIEVAL) + [_handoff_tool("triage")],
        system_prompt=(
            "Tu es l'agent de recherche : documents, graphe de connaissances, vecteur. "
            "Collecte le contexte pertinent avec tes outils, puis passe la main UNE SEULE FOIS "
            "via handoff_to_triage pour la décision. "
            "Si triage te délègue à nouveau, réponds directement sans repasser la main — "
            "évite toute boucle infinie. "
            "Avant toute écriture de fichier, demande validation."
        ),
        name="research",
    )
    g = StateGraph(_SwarmState)
    g.add_node("triage", triage)
    g.add_node("research", research)
    g.add_edge(START, "triage")
    g.add_edge("triage", END)
    g.add_edge("research", END)
    return g.compile(checkpointer=checkpointer)
