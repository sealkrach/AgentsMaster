"""Modèles SQLAlchemy pour le registre agentique."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from pgvector.sqlalchemy import Vector

from .database import Base

EMBEDDING_DIM = 1536


class MCPStatus(str, enum.Enum):
    sandbox = "sandbox"
    validated = "validated"
    promoted = "promoted"
    deprecated = "deprecated"


class MCP(Base):
    __tablename__ = "mcps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    mcp_code = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)
    human_feedback_score = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    bitbucket_synced = Column(Boolean, default=False, nullable=False)
    bitbucket_url = Column(Text, nullable=True)
    feedback = Column(JSONB, default=list, nullable=False)
    status = Column(Enum(MCPStatus), default=MCPStatus.sandbox, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "quality_score": self.quality_score,
            "human_feedback_score": self.human_feedback_score,
            "usage_count": self.usage_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MCPExecution(Base):
    __tablename__ = "mcp_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mcp_id = Column(UUID(as_uuid=True), ForeignKey("mcps.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=True)
    question = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    sources_queried = Column(JSONB, nullable=True)
    result_score = Column(Float, nullable=True)
    otel_trace_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ConnectorSpec(Base):
    __tablename__ = "connector_specs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    kind = Column(String, nullable=False)          # http_api | sql_http | grpc …
    spec_yaml = Column(Text, nullable=False)
    capabilities = Column(JSONB, default=list, nullable=False)   # ["logs", "traces", ...]
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "kind": self.kind,
            "capabilities": self.capabilities,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
