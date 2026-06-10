"""Création initiale du registre agentique (S1).

Revision ID: 001
Revises:
Create Date: 2026-06-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # pgvector extension first
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # mcps — inclut la colonne vector(1536) directement en SQL brut
    op.execute("""
        CREATE TABLE IF NOT EXISTS mcps (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            embedding   vector(1536),
            mcp_code    TEXT,
            version     INTEGER NOT NULL DEFAULT 1,
            quality_score         FLOAT   NOT NULL DEFAULT 0.0,
            human_feedback_score  FLOAT,
            usage_count INTEGER NOT NULL DEFAULT 0,
            last_executed  TIMESTAMPTZ,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            bitbucket_synced BOOLEAN NOT NULL DEFAULT false,
            bitbucket_url    TEXT,
            feedback    JSONB NOT NULL DEFAULT '[]'::jsonb,
            status      TEXT  NOT NULL DEFAULT 'sandbox'
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcps_name   ON mcps (name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mcps_status ON mcps (status)")
    # IVFFLAT cosine index — listes ≈ sqrt(nb_lignes) attendues
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mcps_embedding_ivfflat "
        "ON mcps USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS mcp_executions (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mcp_id       UUID NOT NULL REFERENCES mcps(id) ON DELETE CASCADE,
            version      INTEGER,
            question     TEXT,
            latency_ms   INTEGER,
            tokens_used  INTEGER,
            sources_queried JSONB,
            result_score    FLOAT,
            otel_trace_id   TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_exec_mcp_id ON mcp_executions (mcp_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS connector_specs (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name         TEXT NOT NULL UNIQUE,
            kind         TEXT NOT NULL,
            spec_yaml    TEXT NOT NULL,
            capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
            version      INTEGER NOT NULL DEFAULT 1,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_connectors_name ON connector_specs (name)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mcp_executions")
    op.execute("DROP TABLE IF EXISTS mcps")
    op.execute("DROP TABLE IF EXISTS connector_specs")
