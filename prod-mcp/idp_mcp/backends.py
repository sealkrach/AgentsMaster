"""Clients vers les vrais moteurs (créés paresseusement). Imports lourds différés."""
from __future__ import annotations

import asyncio

from . import config

# ---- PostgreSQL (asyncpg) ---------------------------------------------------
_pg_pool = None
_pg_lock = asyncio.Lock()


async def _pool():
    global _pg_pool
    if _pg_pool is None:
        async with _pg_lock:
            if _pg_pool is None:
                import asyncpg
                if not config.PG_DSN:
                    raise RuntimeError("IDP_PG_DSN non défini")
                _pg_pool = await asyncpg.create_pool(
                    dsn=config.PG_DSN, min_size=1, max_size=5,
                    command_timeout=config.PG_STATEMENT_TIMEOUT_S,
                    server_settings={"default_transaction_read_only": "on"},
                )
    return _pg_pool


async def pg_fetch(sql: str, *args, cap: int | None = None) -> list[dict]:
    pool = await _pool()
    cap = cap or config.ROW_CAP
    async with pool.acquire() as con:
        async with con.transaction(readonly=True):   # garde transactionnelle
            rows = await con.fetch(sql, *args)
    return [dict(r) for r in rows[:cap]]


# ---- ArangoDB (python-arango, synchrone) ------------------------------------
_arango_db = None


def arango_db():
    global _arango_db
    if _arango_db is None:
        from arango import ArangoClient
        client = ArangoClient(hosts=config.ARANGO_URL)
        _arango_db = client.db(
            config.ARANGO_DB, username=config.ARANGO_USER, password=config.ARANGO_PASSWORD
        )
    return _arango_db


# ---- Qdrant (async) ---------------------------------------------------------
_qdrant = None


def qdrant_client():
    global _qdrant
    if _qdrant is None:
        from qdrant_client import AsyncQdrantClient
        _qdrant = AsyncQdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    return _qdrant


# ---- Embedding (doit matcher l'index Qdrant) --------------------------------
_emb_cache: dict = {}


async def embed(text: str) -> list[float]:
    p = config.EMBEDDING_PROVIDER.lower()
    if p == "http":
        import httpx
        if not config.EMBEDDING_ENDPOINT:
            raise RuntimeError("IDP_EMBEDDING_ENDPOINT requis pour provider=http")
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                config.EMBEDDING_ENDPOINT,
                json={"model": config.EMBEDDING_MODEL, "input": text},
            )
            r.raise_for_status()
            data = r.json()
            # Adaptez au format de VOTRE service (ici style OpenAI/Bedrock embeddings).
            return data["data"][0]["embedding"] if "data" in data else data["embedding"]
    if p == "fastembed":
        if "fe" not in _emb_cache:
            from fastembed import TextEmbedding
            _emb_cache["fe"] = TextEmbedding(
                model_name=config.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5"
            )
        return list(next(_emb_cache["fe"].embed([text])))
    raise RuntimeError(
        "IDP_EMBEDDING_PROVIDER doit être 'http' ou 'fastembed' et correspondre "
        "au modèle ayant indexé Qdrant."
    )
