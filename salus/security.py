"""Security helpers: auth, validation, rate limiting, headers."""

from __future__ import annotations

import re
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from salus.config import settings

# Safe identifiers for graph / org entities (never interpolate raw into Cypher).
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+\-]{0,127}$")
PERSON_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 .'\-]{0,79}$")
TICKET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_]{0,31}$")
SEVERITIES = frozenset({"SEV-1", "SEV-2", "SEV-3", "SEV-4", "P0", "P1", "P2", "P3"})
ESCALATE_MODES = frozenset({"page_owner", "severity", "manager", "sre", "assign"})
EXPORT_FORMATS = frozenset(
    {
        "graph_json",
        "graph_csv",
        "graphml",
        "embedding",
        "evidence_embedding",
        "report_md",
        "markdown",
        "report_html",
        "html",
    }
)
DOMAINS = frozenset(
    {"finance", "healthcare", "security", "facilities", "ops", "identity"}
)

PUBLIC_PATHS = frozenset({"/", "/api/health", "/favicon.ico"})
PUBLIC_PREFIXES = ("/static/",)


class RateLimiter:
    def __init__(self, limit: int, window_sec: float) -> None:
        self.limit = limit
        self.window = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                raise HTTPException(429, "Rate limit exceeded. Try again shortly.")
            q.append(now)


ask_limiter = RateLimiter(limit=30, window_sec=60.0)
mutate_limiter = RateLimiter(limit=20, window_sec=60.0)
general_limiter = RateLimiter(limit=120, window_sec=60.0)


def client_ip(request: Request) -> str:
    if settings.trust_x_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Enforce API key unless auth is explicitly disabled (local-only)."""
    if settings.auth_disabled:
        return
    expected = settings.api_key
    if not expected:
        raise HTTPException(503, "Server API key is not configured")
    provided = x_api_key or request.query_params.get("api_key")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(401, "Invalid or missing API key")


def require_admin_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Seed/admin routes: prefer dedicated admin key; otherwise API key is enough."""
    if settings.auth_disabled:
        return
    if settings.admin_key:
        if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_key):
            raise HTTPException(403, "Admin key required")
        return
    require_api_key(request, x_api_key)


def validate_id(value: str | None, field: str = "id") -> str | None:
    if value is None or value == "":
        return None
    if not ID_RE.match(value):
        raise ValueError(f"Invalid {field}")
    return value


def validate_person(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not PERSON_RE.match(value):
        raise ValueError("Invalid person_name")
    return value


def validate_ticket(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not TICKET_RE.match(value):
        raise ValueError("Invalid ticket_key")
    return value


def validate_severity(value: str) -> str:
    if value not in SEVERITIES:
        raise ValueError("Invalid severity")
    return value


def validate_question(value: str) -> str:
    q = value.strip()
    if not q:
        raise ValueError("Question required")
    if len(q) > settings.max_question_chars:
        raise ValueError(f"Question too long (max {settings.max_question_chars})")
    # Block obvious Cypher injection payloads pasted into chat
    lowered = q.lower()
    for bad in ("detach delete", " drop ", "create index", "load csv", " call dbms"):
        if bad in lowered:
            raise ValueError("Question contains disallowed content")
    return q


def validate_reason(value: str) -> str:
    reason = (value or "").strip()
    if len(reason) > 500:
        raise ValueError("Reason too long")
    return reason


def locked_tenant(requested: str | None) -> str:
    """Ignore client-supplied tenants unless explicitly allowlisted."""
    if not requested or requested == settings.tenant_id:
        return settings.tenant_id
    if requested in settings.allowed_tenants:
        if not ID_RE.match(requested):
            raise HTTPException(400, "Invalid tenant_id")
        return requested
    raise HTTPException(403, "Tenant not allowed")


def as_http(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ValueError):
        return HTTPException(400, str(exc))
    return HTTPException(500, sanitize_error(exc))


def sanitize_error(exc: Exception) -> str:
    if settings.debug:
        return str(exc)[:500]
    return "Internal error"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Basic rate limit for all API traffic
        path = request.url.path
        if path.startswith("/api/"):
            try:
                general_limiter.check(f"gen:{client_ip(request)}")
            except HTTPException as e:
                return Response(e.detail, status_code=e.status_code)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        # CSP: allow self + Google Fonts + cytoscape CDN used by UI
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


def assert_path_public_or_authed(request: Request) -> bool:
    path = request.url.path
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)
