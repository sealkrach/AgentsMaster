"""Registre sémantique des MCPs.

Opérations principales :
  semantic_search  — recherche cosinus via pgvector
  save_mcp         — crée ou verse une nouvelle version
  record_execution — trace une exécution
  save_connector   — upsert d'un ConnectorSpec
  list_mcps        — liste paginée

Seuils spec (§4.3) :
  ≥ 0.85 → réutiliser le MCP existant
  0.70–0.85 → proposer et demander confirmation
  < 0.70 → générer un nouveau MCP
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MCP, MCPExecution, ConnectorSpec, MCPStatus

REUSE_THRESHOLD = 0.85
PROPOSE_THRESHOLD = 0.70


@dataclass
class MCPMatch:
    mcp: MCP
    score: float

    @property
    def recommendation(self) -> str:
        if self.score >= REUSE_THRESHOLD:
            return "reuse"
        if self.score >= PROPOSE_THRESHOLD:
            return "propose"
        return "generate"


async def semantic_search(
    session: AsyncSession,
    query: str,
    limit: int = 5,
) -> list[MCPMatch]:
    """Cosine similarity search via pgvector operator (<=>)."""
    from .embeddings import embed

    vec = await embed(query)
    vec_str = "[" + ",".join(str(x) for x in vec) + "]"

    stmt = text("""
        SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM mcps
        WHERE status != 'deprecated'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :limit
    """)
    rows = (await session.execute(stmt, {"vec": vec_str, "limit": limit})).fetchall()

    results: list[MCPMatch] = []
    for row in rows:
        mcp = await session.get(MCP, row.id)
        if mcp:
            results.append(MCPMatch(mcp=mcp, score=float(row.score)))
    return results


async def save_mcp(
    session: AsyncSession,
    name: str,
    description: str,
    code: str,
) -> MCP:
    """Create or version-bump a MCP. Embedding is generated on save."""
    from .embeddings import embed

    embedding_text = f"{name} {description}"
    try:
        vec = await embed(embedding_text)
    except RuntimeError:
        vec = None  # Embedding unavailable — semantic search won't work for this entry

    existing = (await session.execute(select(MCP).where(MCP.name == name))).scalar_one_or_none()

    if existing:
        existing.version += 1
        existing.mcp_code = code
        existing.description = description
        if vec is not None:
            existing.embedding = vec
        existing.status = MCPStatus.sandbox
        await session.commit()
        await session.refresh(existing)
        return existing

    mcp = MCP(
        name=name,
        description=description,
        mcp_code=code,
        embedding=vec,
    )
    session.add(mcp)
    await session.commit()
    await session.refresh(mcp)
    return mcp


async def record_execution(
    session: AsyncSession,
    mcp_id: uuid.UUID,
    **kwargs: Any,
) -> MCPExecution:
    exec_ = MCPExecution(mcp_id=mcp_id, **kwargs)
    session.add(exec_)
    await session.commit()
    return exec_


async def list_mcps(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    status: MCPStatus | None = None,
) -> list[MCP]:
    stmt = select(MCP).order_by(MCP.created_at.desc()).offset(offset).limit(limit)
    if status:
        stmt = stmt.where(MCP.status == status)
    return (await session.execute(stmt)).scalars().all()


async def save_connector(
    session: AsyncSession,
    name: str,
    kind: str,
    spec_yaml: str,
    capabilities: list[str],
) -> ConnectorSpec:
    existing = (
        await session.execute(select(ConnectorSpec).where(ConnectorSpec.name == name))
    ).scalar_one_or_none()

    if existing:
        existing.spec_yaml = spec_yaml
        existing.capabilities = capabilities
        existing.version += 1
        await session.commit()
        await session.refresh(existing)
        return existing

    spec = ConnectorSpec(name=name, kind=kind, spec_yaml=spec_yaml, capabilities=capabilities)
    session.add(spec)
    await session.commit()
    await session.refresh(spec)
    return spec


async def get_connectors_by_capability(
    session: AsyncSession,
    capability: str,
) -> list[ConnectorSpec]:
    stmt = select(ConnectorSpec).where(ConnectorSpec.capabilities.contains([capability]))
    return (await session.execute(stmt)).scalars().all()
