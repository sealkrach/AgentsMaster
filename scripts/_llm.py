"""Helper provider-agnostic pour les scripts de génération.

Lit LAB_MODEL (format provider:model) et dispatche vers le SDK approprié.

Providers supportés :
  anthropic:claude-sonnet-4-6        → Anthropic SDK
  openai:gpt-4o                      → OpenAI SDK
  openai:llama3 + OPENAI_BASE_URL=…  → tout endpoint OpenAI-compatible
                                       (Ollama, vLLM, Azure, LM Studio, OpenRouter…)
"""
from __future__ import annotations

import os
import sys


def call_llm(system: str, user: str, max_tokens: int = 2048) -> str:
    """Appel LLM unifié. Lève une exception en cas d'erreur."""
    spec = os.getenv("LAB_MODEL", "anthropic:claude-sonnet-4-6").strip()
    provider, _, model = spec.partition(":")
    if not model:
        provider, model = "openai", spec
    if provider == "anthropic":
        return _call_anthropic(system, user, model, max_tokens)
    return _call_openai(system, user, model, max_tokens)


def _call_anthropic(system: str, user: str, model: str, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError:
        print("Erreur : 'anthropic' n'est pas installé. Exécutez : make install")
        sys.exit(1)
    try:
        client = anthropic.Anthropic()
    except Exception:
        print("Erreur : ANTHROPIC_API_KEY absent ou invalide. Ajoutez-le à votre .env.")
        sys.exit(1)
    try:
        r = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as e:
        raise RuntimeError(f"Anthropic API : {e}") from e
    return r.content[0].text


def _call_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        print("Erreur : 'openai' n'est pas installé. Exécutez : make install")
        sys.exit(1)
    kw: dict = {}
    if base_url := os.getenv("OPENAI_BASE_URL"):
        kw["base_url"] = base_url
    try:
        client = OpenAI(**kw)
    except Exception:
        print("Erreur : OPENAI_API_KEY absent ou invalide. Ajoutez-le à votre .env.")
        sys.exit(1)
    try:
        r = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI API : {e}") from e
    return r.choices[0].message.content
