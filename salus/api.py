"""SALUS web API — host the agent UI and stream live runs."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from salus import actions, algorithms, export_pack
from salus.agents import run_salus
from salus.config import settings
from salus.graph import query
from salus.security import (
    DOMAINS,
    ESCALATE_MODES,
    EXPORT_FORMATS,
    SecurityHeadersMiddleware,
    ask_limiter,
    client_ip,
    locked_tenant,
    mutate_limiter,
    require_admin_key,
    require_api_key,
    sanitize_error,
    validate_id,
    validate_person,
    validate_question,
    validate_reason,
    validate_severity,
    validate_ticket,
)
from salus.seed import load_seed
from salus.tools import list_systems

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        n = query("MATCH (n) RETURN count(n)", readonly=True)[0][0]
        if not n:
            load_seed(reset=True)
    except Exception:
        try:
            load_seed(reset=True)
        except Exception:
            pass
    yield


app = FastAPI(
    title="SALUS",
    version="0.3.0",
    description="Universal org nerve agent",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if not settings.is_production else list(settings.allowed_hosts),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key", "X-OpenAI-Key"],
    max_age=600,
)


def _openai_key_from_request(request: Request, body_key: str | None = None) -> str | None:
    """Prefer per-request header/body key; never log it. Falls back to env in tool_router."""
    header = request.headers.get("x-openai-key")
    query_key = request.query_params.get("openai_key")
    for candidate in (body_key, header, query_key):
        if candidate and candidate.strip():
            key = candidate.strip()
            if len(key) > 200:
                raise HTTPException(400, "OpenAI key too long")
            if not key.startswith("sk-"):
                raise HTTPException(400, "OpenAI key format looks invalid")
            return key
    return None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="person:sam", max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    tenant_id: str | None = Field(default=None, max_length=64)
    openai_api_key: str | None = Field(default=None, max_length=200)

    @field_validator("user_id")
    @classmethod
    def _user(cls, v: str) -> str:
        return validate_id(v, "user_id") or "person:sam"

    @field_validator("session_id")
    @classmethod
    def _sess(cls, v: str | None) -> str | None:
        return validate_id(v, "session_id")


class EscalateRequest(BaseModel):
    mode: str = Field(..., max_length=32)
    system_name: str | None = Field(default=None, max_length=128)
    person_name: str | None = Field(default=None, max_length=80)
    ticket_key: str | None = Field(default=None, max_length=32)
    severity: str = Field(default="SEV-1", max_length=16)
    reason: str = Field(default="", max_length=500)
    tenant_id: str | None = Field(default=None, max_length=64)

    @field_validator("mode")
    @classmethod
    def _mode(cls, v: str) -> str:
        mode = v.strip().lower()
        if mode not in ESCALATE_MODES:
            raise ValueError("Invalid escalate mode")
        return mode

    @field_validator("system_name")
    @classmethod
    def _sys(cls, v: str | None) -> str | None:
        return validate_id(v, "system_name")

    @field_validator("person_name")
    @classmethod
    def _person(cls, v: str | None) -> str | None:
        return validate_person(v)

    @field_validator("ticket_key")
    @classmethod
    def _ticket(cls, v: str | None) -> str | None:
        return validate_ticket(v)

    @field_validator("severity")
    @classmethod
    def _sev(cls, v: str) -> str:
        return validate_severity(v)

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        return validate_reason(v)


class ExportRequest(BaseModel):
    format: str = Field(..., max_length=32)
    system: str | None = Field(default=None, max_length=128)
    result: dict[str, Any] | None = None
    tenant_id: str | None = Field(default=None, max_length=64)

    @field_validator("format")
    @classmethod
    def _fmt(cls, v: str) -> str:
        fmt = v.strip().lower()
        if fmt not in EXPORT_FORMATS:
            raise ValueError("Invalid export format")
        return fmt

    @field_validator("system")
    @classmethod
    def _sys(cls, v: str | None) -> str | None:
        return validate_id(v, "system")

    @field_validator("result")
    @classmethod
    def _result_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        # Cap client-supplied result payload size
        raw = json.dumps(v, default=str)
        if len(raw) > 200_000:
            raise ValueError("result payload too large")
        return v


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        n = query("MATCH (n) RETURN count(n)", readonly=True)[0][0]
        return {
            "ok": True,
            "graph": settings.graph_name,
            "nodes": n,
            "auth_required": not settings.auth_disabled,
        }
    except Exception:
        return {
            "ok": False,
            "error": "graph unavailable",
            "graph": settings.graph_name,
            "auth_required": not settings.auth_disabled,
        }


@app.get("/api/auth/config")
def auth_config() -> dict[str, Any]:
    """Public bootstrap: whether the UI must send an API key (never returns the key)."""
    return {
        "auth_required": not settings.auth_disabled,
        "hint": None if settings.is_production else "Set X-API-Key from SALUS_API_KEY",
    }


@app.post("/api/seed")
def seed(
    request: Request,
    reset: bool = True,
    _: None = Depends(require_admin_key),
) -> dict[str, Any]:
    mutate_limiter.check(f"seed:{client_ip(request)}")
    name = load_seed(reset=reset)
    return {"graph": name, "ok": True}


@app.get("/api/systems")
def systems(
    request: Request,
    domain: str | None = None,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    if domain and domain not in DOMAINS:
        raise HTTPException(400, "Invalid domain")
    return list_systems(domain=domain)


@app.get("/api/graph")
def graph_payload(
    request: Request,
    focus: str | None = Query(None, max_length=128),
    tenant_id: str | None = Query(None, max_length=64),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    try:
        focus = validate_id(focus, "focus")
        tenant = locked_tenant(tenant_id)
    except Exception as e:
        from salus.security import as_http

        raise as_http(e) from e
    sys_rows = query(
        """
        MATCH (s:System)
        RETURN s.id, s.name, s.domain, s.criticality, s.kind
        """,
        readonly=True,
        tenant_id=tenant,
    )
    dep_rows = query(
        """
        MATCH (a:System)-[r:DEPENDS_ON]->(b:System)
        RETURN a.name, b.name, r.kind
        """,
        readonly=True,
        tenant_id=tenant,
    )
    own_rows = query(
        """
        MATCH (p:Person)-[:OWNS]->(s:System)
        RETURN p.id, p.name, p.role, s.name
        """,
        readonly=True,
        tenant_id=tenant,
    )

    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sid, name, domain, crit, kind in sys_rows:
        nodes.append(
            {
                "id": name,
                "label": name,
                "kind": "system",
                "domain": domain,
                "criticality": crit,
                "system_kind": kind,
                "focused": bool(focus and name == focus),
            }
        )
        seen.add(name)

    for pid, pname, role, sname in own_rows:
        if pid not in seen:
            nodes.append(
                {
                    "id": pid,
                    "label": pname,
                    "kind": "person",
                    "role": role,
                    "focused": False,
                }
            )
            seen.add(pid)

    edges: list[dict[str, Any]] = []
    for a, b, kind in dep_rows:
        edges.append(
            {
                "id": f"{a}->{b}",
                "source": a,
                "target": b,
                "kind": "DEPENDS_ON",
                "rel": kind or "sync",
            }
        )
    for pid, pname, role, sname in own_rows:
        edges.append(
            {
                "id": f"{pid}-owns-{sname}",
                "source": pid,
                "target": sname,
                "kind": "OWNS",
                "rel": "owns",
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "focus": focus,
        "graph": settings.graph_name,
        "agents": [
            {"id": "router", "label": "Router", "role": "classify + handoff"},
            {"id": "investigator", "label": "Investigator", "role": "multi-hop + algorithms"},
            {"id": "actor", "label": "Actor", "role": "page / assign / open"},
            {"id": "scribe", "label": "Scribe", "role": "episode + fact memory"},
        ],
    }


@app.get("/api/path")
def path_find(
    source: str = Query(..., max_length=128),
    target: str = Query(..., max_length=128),
    tenant_id: str | None = Query(None, max_length=64),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    """Shortest DEPENDS_ON path between two systems for the path finder UI."""
    try:
        source = validate_id(source, "source")
        target = validate_id(target, "target")
        tenant = locked_tenant(tenant_id)
    except Exception as e:
        from salus.security import as_http

        raise as_http(e) from e
    result = algorithms.shortest_dependency_path(source, target, tenant_id=tenant)
    return {"graph": settings.graph_name, **result}


def _ask_payload(result) -> dict[str, Any]:
    return {
        "answer": result.answer,
        "domain": result.domain,
        "system": result.system,
        "owners": result.owners,
        "confidence": result.confidence,
        "actions": result.actions,
        "sources": result.sources,
        "evidence_summary": result.evidence_summary,
        "handoffs": result.handoffs,
        "investigation_id": result.investigation_id,
        "session_id": result.session_id,
        "checklist": result.checklist,
        "path": result.path,
        "tool_selection": result.tool_selection,
        "steps": [
            {"agent": s.agent, "action": s.action, "detail": s.detail} for s in result.steps
        ],
    }


@app.post("/api/ask")
def ask(
    body: AskRequest,
    request: Request,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    ask_limiter.check(f"ask:{client_ip(request)}")
    try:
        question = validate_question(body.question)
        tenant = locked_tenant(body.tenant_id)
        openai_key = _openai_key_from_request(request, body.openai_api_key)
        result = run_salus(
            question,
            tenant_id=tenant,
            user_id=body.user_id,
            session_id=body.session_id,
            openai_api_key=openai_key,
        )
    except Exception as e:
        from salus.security import as_http

        raise as_http(e) from e
    return _ask_payload(result)


@app.get("/api/ask/stream")
async def ask_stream(
    request: Request,
    question: str = Query(..., min_length=1, max_length=2000),
    user_id: str = Query(default="person:sam", max_length=128),
    session_id: str | None = Query(default=None, max_length=128),
    tenant_id: str | None = Query(default=None, max_length=64),
    _: None = Depends(require_api_key),
) -> StreamingResponse:
    ask_limiter.check(f"ask:{client_ip(request)}")
    try:
        q_text = validate_question(question)
        user_id = validate_id(user_id, "user_id") or "person:sam"
        session_id = validate_id(session_id, "session_id")
        tenant = locked_tenant(tenant_id)
        openai_key = _openai_key_from_request(request)
    except Exception as e:
        from salus.security import as_http

        raise as_http(e) from e

    q: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            def on_event(evt: dict[str, Any]) -> None:
                q.put(evt)

            run_salus(
                q_text,
                tenant_id=tenant,
                user_id=user_id,
                session_id=session_id,
                on_event=on_event,
                openai_api_key=openai_key,
            )
        except Exception as e:
            q.put({"type": "error", "message": sanitize_error(e)})
        finally:
            q.put({"type": "done"})

    threading.Thread(target=worker, daemon=True).start()

    async def event_gen():
        while True:
            if await request.is_disconnected():
                break
            evt = await asyncio.to_thread(q.get)
            yield f"data: {json.dumps(evt, default=str)}\n\n"
            if evt.get("type") in {"done", "error"}:
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/escalate")
def escalate(
    body: EscalateRequest,
    request: Request,
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    mutate_limiter.check(f"esc:{client_ip(request)}")
    tenant = locked_tenant(body.tenant_id)
    mode = body.mode
    if mode == "page_owner":
        if not body.person_name:
            raise HTTPException(400, "person_name required")
        return actions.page_owner(
            body.person_name,
            ticket_key=body.ticket_key,
            system_name=body.system_name,
            reason=body.reason or "UI escalate: page owner",
            tenant_id=tenant,
        )
    if mode == "severity":
        if not body.ticket_key:
            raise HTTPException(400, "ticket_key required")
        return actions.escalate_severity(
            body.ticket_key,
            body.severity,
            reason=body.reason or "UI escalate severity",
            tenant_id=tenant,
        )
    if mode == "manager":
        if not body.person_name:
            raise HTTPException(400, "person_name required")
        return actions.escalate_to_manager(
            body.person_name,
            system_name=body.system_name,
            reason=body.reason or "UI escalate to manager",
            tenant_id=tenant,
        )
    if mode == "sre":
        if not body.system_name:
            raise HTTPException(400, "system_name required")
        return actions.escalate_to_sre(
            system_name=body.system_name,
            reason=body.reason or "UI escalate to SRE",
            tenant_id=tenant,
        )
    if mode == "assign":
        if not body.ticket_key or not body.person_name:
            raise HTTPException(400, "ticket_key and person_name required")
        return actions.assign_ticket(
            body.ticket_key, body.person_name, tenant_id=tenant
        )
    raise HTTPException(400, "Unknown escalate mode")


@app.post("/api/export")
def export(
    body: ExportRequest,
    request: Request,
    _: None = Depends(require_api_key),
):
    mutate_limiter.check(f"exp:{client_ip(request)}")
    tenant = locked_tenant(body.tenant_id)
    fmt = body.format
    system = body.system
    result = body.result or {}
    if not system and isinstance(result.get("system"), str):
        system = validate_id(result.get("system"), "system")

    if fmt == "graph_json":
        data = export_pack.export_graph_nodes_json(system, tenant)
        return Response(
            json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=salus-graph-nodes.json"},
        )
    if fmt == "graph_csv":
        text = export_pack.export_graph_nodes_csv(system, tenant)
        return PlainTextResponse(
            text,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=salus-graph-nodes.csv"},
        )
    if fmt == "graphml":
        text = export_pack.export_graphml(system, tenant)
        return PlainTextResponse(
            text,
            media_type="application/graphml+xml",
            headers={"Content-Disposition": "attachment; filename=salus-graph.graphml"},
        )
    if fmt in {"embedding", "evidence_embedding"}:
        emb = export_pack.evidence_embedding(result=result, tenant_id=tenant)
        return Response(
            json.dumps(emb, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=salus-evidence-embedding.json"
            },
        )
    if fmt in {"report_md", "markdown"}:
        emb = export_pack.evidence_embedding(result=result, tenant_id=tenant)
        text = export_pack.markdown_report(result, emb)
        return PlainTextResponse(
            text,
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=salus-report.md"},
        )
    if fmt in {"report_html", "html"}:
        emb = export_pack.evidence_embedding(result=result, tenant_id=tenant)
        text = export_pack.html_report(result, emb)
        return Response(
            text,
            media_type="text/html",
            headers={"Content-Disposition": "attachment; filename=salus-report.html"},
        )
    raise HTTPException(400, "Unknown export format")


@app.get("/")
def index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "UI not found")
    return FileResponse(index_path)


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run("salus.api:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
