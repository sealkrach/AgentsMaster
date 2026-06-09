"""Observabilité optionnelle : Arize Phoenix et/ou LangSmith.

Pilotée par variables d'env, tolérante à l'absence : si rien n'est configuré, le
runtime tourne sans tracing (et le signale via /info). Quand c'est branché, chaque
exécution de l'agent (graphe LangGraph) est tracée — sans instrumentation côté skill.
Ne casse JAMAIS le runtime pour un problème de tracing.
"""
from __future__ import annotations

import os

_STATUS: dict = {"enabled": False, "backend": None, "project": None, "url": None}


def setup() -> dict:
    global _STATUS
    # 1) Arize Phoenix (OpenInference) si demandé
    if os.getenv("PHOENIX_ENABLED", "").lower() == "true" or os.getenv("PHOENIX_COLLECTOR_ENDPOINT"):
        try:
            from phoenix.otel import register
            register(auto_instrument=True, project_name=os.getenv("PHOENIX_PROJECT", "agentathon"))
            _STATUS = {
                "enabled": True, "backend": "phoenix",
                "project": os.getenv("PHOENIX_PROJECT", "agentathon"),
                "url": os.getenv("PHOENIX_UI_URL") or os.getenv("PHOENIX_COLLECTOR_ENDPOINT"),
            }
            return dict(_STATUS)
        except Exception as e:  # tracing best-effort
            _STATUS = {"enabled": False, "backend": "phoenix", "project": None,
                       "url": None, "error": str(e)[:200]}
    # 2) LangSmith (auto via env LANGSMITH_TRACING + LANGSMITH_API_KEY)
    if os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "")).lower() == "true":
        _STATUS = {
            "enabled": True, "backend": "langsmith",
            "project": os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "default")),
            "url": "https://smith.langchain.com",
        }
        return dict(_STATUS)
    return dict(_STATUS)


def status() -> dict:
    return dict(_STATUS)
