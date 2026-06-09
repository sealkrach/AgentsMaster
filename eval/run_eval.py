"""Mini-harnais d'eval pour le lab (async).

    python -m eval.run_eval                      # eval du skill par défaut
    python -m eval.run_eval eval/mon-skill.jsonl # un autre jeu

Substring match avec normalisation des accents. En prod, branchez LangSmith : l'agent
étant un graphe LangGraph, ses traces (skills, outils, décisions) y sont exploitables.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import unicodedata
import uuid
from pathlib import Path

from runtime.agent import build_agent

DATASET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/invoice-triage.jsonl")


def _norm(s: str) -> str:
    """Supprime les accents et met en majuscules pour une comparaison robuste."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().upper()


async def run() -> int:
    agent = await build_agent()
    cases = [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]
    passed = 0
    total_ms = 0.0
    for n, case in enumerate(cases, 1):
        t0 = time.monotonic()
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": case["input"]}]},
            config={"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}},
        )
        elapsed = (time.monotonic() - t0) * 1000
        total_ms += elapsed
        msgs = result.get("messages", [])
        raw_answer = msgs[-1].content if msgs else ""
        answer = _norm(raw_answer)
        want = _norm(case["expect_decision"])
        ok = want in answer
        passed += ok
        print(f"[{'✓' if ok else '✗'}] cas {n} ({elapsed:.0f}ms): attendu={want:9s} — {case['note']}")
        if not ok:
            print(f"      réponse (normalisée): {answer[:200]}")
            print(f"      réponse (brute):      {raw_answer[:200]}")
    avg = total_ms / len(cases) if cases else 0
    print(f"\n{passed}/{len(cases)} cas passés  (moy. {avg:.0f}ms/cas).")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
