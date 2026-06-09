"""Couche de service FastAPI du lab.

  POST /invoke   appel synchrone        POST /stream   streaming (SSE)
  GET  /health   readiness              GET  /info     état observable (topo, outils, skills, tracing)
  GET  /         UI de salle de contrôle
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from . import agent as agent_mod
from . import config, observability, skills_index
from .agent import build_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tracing = observability.setup()   # tracing AVANT de construire l'agent
    app.state.agent = await build_agent()
    yield


app = FastAPI(title=config.LAB_TITLE, lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class GenRequest(BaseModel):
    name: str
    description: str
    dry_run: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "team": config.TEAM_NAME,
            "topology": config.LAB_TOPOLOGY, "tools": config.MCP_MODE}


@app.get("/info")
def info(request: Request) -> dict:
    """Tout ce qui rend le runtime observable, pour l'UI."""
    return {
        "title": config.LAB_TITLE,
        "team": config.TEAM_NAME,
        "topology": config.LAB_TOPOLOGY,
        "tools_mode": config.MCP_MODE,
        "mcp_servers": list(config.MCP_SERVERS.keys()),
        "tools": agent_mod.RUNTIME_INFO.get("tools", []),
        "skills": skills_index.list_skills(str(config.SKILLS_DIR)),
        "tracing": getattr(request.app.state, "tracing", observability.status()),
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
        except Exception as e:  # remonte l'erreur à l'UI plutôt que de couper net
            yield _sse({"type": "error", "message": str(e)[:300]})
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(config.REPO_ROOT / "ui" / "index.html"))


async def _stream_script(cmd: list[str]):
    """Lance un script CLI comme subprocess et streame chaque ligne de stdout via SSE."""
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


def _validate_gen_name(name: str) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise HTTPException(400, f"Nom invalide : '{name}'. Utilisez kebab-case.")


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
    _validate_gen_name(req.name)
    cmd = [sys.executable, "scripts/gen_mcp.py",
           "--name", req.name, "--description", req.description]
    if req.dry_run:
        cmd.append("--dry-run")
    return StreamingResponse(_stream_script(cmd), media_type="text/event-stream")


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
