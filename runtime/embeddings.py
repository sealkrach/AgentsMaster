"""Génération d'embeddings texte (OpenAI text-embedding-3-small, 1536 dims)."""
from __future__ import annotations

import os

EMBEDDING_DIM = 1536


async def embed(text: str) -> list[float]:
    """Retourne un vecteur de 1536 dimensions via OpenAI embeddings API."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError("Le package 'openai' est requis. Exécutez : pip install openai")

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY est requis pour la recherche sémantique. "
            "Ajoutez-le dans .env (peut être distinct de LAB_MODEL)."
        )

    base_url = os.getenv("EMBEDDING_BASE_URL") or None
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.embeddings.create(input=text[:8000], model=model)
    return response.data[0].embedding
