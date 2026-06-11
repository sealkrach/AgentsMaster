"""Couche de service FastAPI du lab.

  POST /invoke              appel synchrone    POST /stream          streaming (SSE)
  GET  /health              readiness          GET  /info            état observable
  GET  /llm-status          ping LLM (TTL 60s) POST /restart         recharge l'engine
  GET  /                    UI chat
  POST /gen-skill           génère skill       POST /gen-mcp         génère MCP
  GET  /config              lecture .env       POST /config          écriture .env
  GET  /registry            liste MCPs         GET  /registry/search recherche cosinus
  PATCH /registry/{id}/status change statut   GET  /registry/executions dernières exécs
  GET  /connectors          liste connectors   POST /connectors      upsert connector
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

try:
    import yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from . import agent as agent_mod
from . import config, observability, skills_index
from .agent import build_agent

# ---------------------------------------------------------------------------
# DB setup — graceful si DATABASE_URL absent
# ---------------------------------------------------------------------------

_db_available = False

if config.REGISTRY_ENABLED:
    try:
        from db.database import get_db, init_db
        from db.models import MCP, ConnectorSpec
        from . import registry
        _db_available = True
    except Exception:
        pass


async def _maybe_get_db():
    """FastAPI dependency : retourne une session ou None selon disponibilité DB."""
    if not _db_available:
        yield None
        return
    from db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Bootstrap connector specs depuis connector_specs/*.yaml
# ---------------------------------------------------------------------------

_CONNECTOR_DIR = config.REPO_ROOT / "connector_specs"


async def _bootstrap_connectors(session: AsyncSession) -> None:
    if not _CONNECTOR_DIR.exists() or not _yaml_available:
        return
    for yaml_path in sorted(_CONNECTOR_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            await registry.save_connector(
                session,
                name=data["name"],
                kind=data["kind"],
                spec_yaml=yaml_path.read_text(encoding="utf-8"),
                capabilities=data.get("capabilities", []),
            )
        except Exception as exc:
            print(f"[registry] bootstrap connector '{yaml_path.name}' ignoré : {exc}")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tracing = observability.setup()

    if _db_available:
        try:
            await init_db()
            from db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await _bootstrap_connectors(session)
            print("[registry] DB initialisée.")
        except Exception as exc:
            print(f"[registry] DB indisponible (mode dégradé) : {exc}")

    app.state.agent = await build_agent()
    yield


app = FastAPI(title=config.LAB_TITLE, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class GenRequest(BaseModel):
    name: str
    description: str
    dry_run: bool = False


class ConfigUpdate(BaseModel):
    updates: dict[str, str]


class ConnectorUpsert(BaseModel):
    name: str
    kind: str
    spec_yaml: str
    capabilities: list[str] = []


# ---------------------------------------------------------------------------
# Config helpers (.env)
# ---------------------------------------------------------------------------

_RESTART_KEYS: frozenset[str] = frozenset({
    "LAB_MODEL", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL",
    "LAB_TOPOLOGY", "MCP_MODE", "MCP_HOST", "CHECKPOINT_DB",
    "HITL_WRITE", "HITL_EDIT",
    "PHOENIX_ENABLED", "PHOENIX_COLLECTOR_ENDPOINT",
    "LANGSMITH_TRACING", "LANGSMITH_API_KEY",
    "DATABASE_URL", "EMBEDDING_MODEL", "EMBEDDING_BASE_URL",
})
_SECRET_KEYS: frozenset[str] = frozenset({
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LANGSMITH_API_KEY",
})


def _read_dotenv() -> dict[str, str]:
    path = config.REPO_ROOT / ".env"
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_dotenv(data: dict[str, str]) -> None:
    path = config.REPO_ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in data:
                new_lines.append(f"{k}={data[k]}")
                updated.add(k)
                continue
        new_lines.append(line)
    for k, v in data.items():
        if k not in updated:
            new_lines.append(f"{k}={v}")
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "team": config.TEAM_NAME,
        "topology": config.LAB_TOPOLOGY,
        "tools": config.MCP_MODE,
        "registry": _db_available,
    }


@app.get("/info")
def info(request: Request) -> dict:
    return {
        "title": config.LAB_TITLE,
        "team": config.TEAM_NAME,
        "topology": config.LAB_TOPOLOGY,
        "tools_mode": config.MCP_MODE,
        "mcp_servers": list(config.MCP_SERVERS.keys()),
        "tools": agent_mod.RUNTIME_INFO.get("tools", []),
        "skills": skills_index.list_skills(str(config.SKILLS_DIR)),
        "tracing": getattr(request.app.state, "tracing", observability.status()),
        "registry": _db_available,
    }


@app.post("/invoke")
async def invoke(req: ChatRequest, request: Request) -> dict:
    thread_id = req.thread_id or str(uuid.uuid4())
    result = await request.app.state.agent.ainvoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    msgs = result.get("messages", [])
    return {"thread_id": thread_id, "answer": msgs[-1].content if msgs else ""}


@app.post("/stream")
async def stream(req: ChatRequest, request: Request) -> StreamingResponse:
    agent = request.app.state.agent
    thread_id = req.thread_id or str(uuid.uuid4())

    async def gen():
        yield _sse({"type": "thread", "thread_id": thread_id})
        try:
            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": req.message}]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="updates",
            ):
                for node, payload in chunk.items():
                    yield _sse({"type": "update", "node": node, "payload": _safe(payload)})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)[:300]})
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(config.REPO_ROOT / "ui" / "index.html"))


# ---------------------------------------------------------------------------
# Generation endpoints (SSE streaming)
# ---------------------------------------------------------------------------

def _validate_gen_name(name: str) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise HTTPException(400, f"Nom invalide : '{name}'. Utilisez kebab-case.")


async def _stream_script(cmd: list[str]):
    """Lance un script CLI et streame chaque ligne de stdout en SSE."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(config.REPO_ROOT),
    )
    assert proc.stdout
    async for raw in proc.stdout:
        line = raw.decode(errors="replace").rstrip()
        if line:
            yield _sse({"type": "gen:line", "text": line})
    await proc.wait()
    yield _sse({"type": "gen:done" if proc.returncode == 0 else "gen:error",
                "code": proc.returncode})


@app.post("/gen-skill")
async def gen_skill(req: GenRequest) -> StreamingResponse:
    _validate_gen_name(req.name)
    cmd = [sys.executable, "scripts/gen_skill.py",
           "--name", req.name, "--description", req.description]
    if req.dry_run:
        cmd.append("--dry-run")
    return StreamingResponse(_stream_script(cmd), media_type="text/event-stream")


@app.post("/gen-mcp")
async def gen_mcp_endpoint(req: GenRequest) -> StreamingResponse:
    """Génère un MCP puis le sauvegarde dans le registre si disponible."""
    _validate_gen_name(req.name)
    cmd = [sys.executable, "scripts/gen_mcp.py",
           "--name", req.name, "--description", req.description]
    if req.dry_run:
        cmd.append("--dry-run")

    async def gen():
        registry_payload: dict | None = None
        async for event in _stream_script(cmd):
            # Intercepte le marqueur [REGISTRY:json] sans le montrer à l'UI
            if '"type": "gen:line"' in event:
                try:
                    d = json.loads(event[6:].strip())
                    line_text = d.get("text", "")
                    if line_text.startswith("[REGISTRY:") and line_text.endswith("]"):
                        registry_payload = json.loads(line_text[len("[REGISTRY:"):-1])
                        continue   # ne pas forwarder cette ligne à l'UI
                except Exception:
                    pass
            yield event

        # Sauvegarde dans le registre si DB disponible et génération réussie
        if registry_payload and _db_available and not req.dry_run:
            try:
                from db.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    mcp = await registry.save_mcp(
                        session,
                        name=registry_payload["name"],
                        description=registry_payload["description"],
                        code=registry_payload["code"],
                    )
                yield _sse({"type": "registry:saved", "mcp_id": str(mcp.id),
                            "name": mcp.name, "version": mcp.version})
            except Exception as exc:
                yield _sse({"type": "registry:error", "message": str(exc)[:300]})

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

@app.get("/config")
def get_config() -> dict:
    current = _read_dotenv()
    for k in (*_RESTART_KEYS, "LAB_TITLE", "TEAM_NAME"):
        if k not in current:
            current[k] = os.getenv(k, "")
    for k in _SECRET_KEYS:
        if current.get(k):
            current[k] = "••••"
    return current


@app.post("/config")
async def post_config(req: ConfigUpdate) -> dict:
    filtered = {k: v for k, v in req.updates.items() if v != "••••"}
    _write_dotenv(filtered)
    restart = [k for k in filtered if k in _RESTART_KEYS]
    return {"saved": list(filtered.keys()), "restart_required": restart}


# ---------------------------------------------------------------------------
# Engine restart + LLM status
# ---------------------------------------------------------------------------

@app.post("/restart")
async def restart_engine() -> dict:
    """Remplace le process courant par une nouvelle instance (os.execv)."""
    async def _do_restart():
        await asyncio.sleep(0.4)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    asyncio.create_task(_do_restart())
    return {"status": "restarting"}


_llm_cache: dict = {"ts": 0.0, "result": None}


@app.get("/llm-status")
async def llm_status() -> dict:
    """Ping léger du LLM configuré. Résultat mis en cache 60 secondes."""
    if _llm_cache["result"] and time.time() - _llm_cache["ts"] < 60:
        return _llm_cache["result"]

    t0 = time.time()
    try:
        scripts_dir = str(config.REPO_ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from _llm import call_llm  # noqa: PLC0415
        config.require_model()
        call_llm("Tu es un assistant.", "Réponds uniquement 'ok'.", max_tokens=5)
        result: dict = {
            "status": "ok",
            "model": config.LAB_MODEL,
            "latency_ms": int((time.time() - t0) * 1000),
        }
    except Exception as exc:
        result = {
            "status": "error",
            "model": config.LAB_MODEL,
            "error": str(exc)[:200],
            "latency_ms": int((time.time() - t0) * 1000),
        }
    _llm_cache["ts"] = time.time()
    _llm_cache["result"] = result
    return result


# ---------------------------------------------------------------------------
# Registry endpoints
# ---------------------------------------------------------------------------

@app.get("/registry")
async def get_registry(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        return {"items": [], "registry_enabled": False}
    from db.models import MCPStatus
    status_filter = MCPStatus(status) if status else None
    items = await registry.list_mcps(session, offset=offset, limit=limit, status=status_filter)
    return {
        "items": [m.to_dict() for m in items],
        "offset": offset,
        "limit": limit,
        "registry_enabled": True,
    }


@app.get("/registry/search")
async def search_registry(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=20),
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        return {"matches": [], "registry_enabled": False}
    try:
        matches = await registry.semantic_search(session, query=q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    return {
        "query": q,
        "matches": [
            {
                **m.mcp.to_dict(),
                "score": round(m.score, 4),
                "recommendation": m.recommendation,
            }
            for m in matches
        ],
        "registry_enabled": True,
    }


class StatusUpdate(BaseModel):
    status: str


@app.patch("/registry/{mcp_id}/status")
async def update_mcp_status(
    mcp_id: str,
    req: StatusUpdate,
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        raise HTTPException(503, "Registry non configuré.")
    from db.models import MCPStatus  # noqa: PLC0415
    try:
        new_status = MCPStatus(req.status)
    except ValueError:
        raise HTTPException(400, f"Statut invalide : {req.status}")
    from sqlalchemy import update as sa_update  # noqa: PLC0415
    from db.models import MCP as MCPModel      # noqa: PLC0415
    await session.execute(
        sa_update(MCPModel)
        .where(MCPModel.id == mcp_id)
        .values(status=new_status)
    )
    await session.commit()
    return {"id": mcp_id, "status": req.status}


@app.get("/registry/executions")
async def get_executions(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        return {"items": [], "registry_enabled": False}
    from sqlalchemy import select, text as sa_text  # noqa: PLC0415
    from db.models import MCPExecution, MCP as MCPModel  # noqa: PLC0415
    stmt = sa_text("""
        SELECT e.id, e.mcp_id, m.name AS mcp_name, e.question,
               e.latency_ms, e.tokens_used, e.result_score, e.created_at
        FROM mcp_executions e
        LEFT JOIN mcps m ON m.id = e.mcp_id
        ORDER BY e.created_at DESC
        LIMIT :limit
    """)
    rows = (await session.execute(stmt, {"limit": limit})).mappings().all()
    items = [
        {
            "id": str(r["id"]),
            "mcp_id": str(r["mcp_id"]),
            "mcp_name": r["mcp_name"],
            "question": (r["question"] or "")[:120],
            "latency_ms": r["latency_ms"],
            "tokens_used": r["tokens_used"],
            "result_score": r["result_score"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
    return {"items": items, "registry_enabled": True}


# ---------------------------------------------------------------------------
# Connector endpoints
# ---------------------------------------------------------------------------

@app.get("/connectors")
async def get_connectors(
    capability: str | None = Query(None),
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        return {"items": [], "registry_enabled": False}
    from sqlalchemy import select
    from db.models import ConnectorSpec
    if capability:
        items = await registry.get_connectors_by_capability(session, capability)
    else:
        from sqlalchemy import select
        items = (await session.execute(select(ConnectorSpec).order_by(ConnectorSpec.name))).scalars().all()
    return {"items": [c.to_dict() for c in items], "registry_enabled": True}


@app.post("/connectors")
async def upsert_connector(
    req: ConnectorUpsert,
    session: AsyncSession | None = Depends(_maybe_get_db),
) -> dict:
    if not _db_available or session is None:
        raise HTTPException(503, "Registry (DATABASE_URL) non configuré.")
    spec = await registry.save_connector(
        session,
        name=req.name,
        kind=req.kind,
        spec_yaml=req.spec_yaml,
        capabilities=req.capabilities,
    )
    return spec.to_dict()


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False, default=str)}\n\n"


def _safe(payload):
    try:
        msgs = payload.get("messages", []) if isinstance(payload, dict) else []
        out = [{"role": getattr(m, "type", "?"), "content": getattr(m, "content", str(m)),
                "name": getattr(m, "name", None),
                "tool_calls": getattr(m, "tool_calls", None)} for m in msgs]
        return {"messages": out} if out else str(payload)
    except Exception:
        return str(payload)
