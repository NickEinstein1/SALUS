"""SALUS configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str) -> frozenset[str]:
    raw = os.getenv(name, "")
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def _on_vercel() -> bool:
    return _bool("VERCEL", False) or bool(os.getenv("VERCEL_ENV"))


def _api_key() -> str:
    env = os.getenv("SALUS_API_KEY", "").strip()
    if env:
        return env
    # Stable-enough local default so UI can work; override in production.
    return "salus-dev-change-me"


def _default_cors() -> frozenset[str]:
    origins = {
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    }
    # Same-origin Vercel deploys do not need CORS, but preview + custom domains do.
    vercel_url = (os.getenv("VERCEL_URL") or "").strip()
    if vercel_url:
        origins.add(f"https://{vercel_url}")
    branch = (os.getenv("VERCEL_BRANCH_URL") or "").strip()
    if branch:
        origins.add(f"https://{branch}")
    project = (os.getenv("VERCEL_PROJECT_PRODUCTION_URL") or "").strip()
    if project:
        origins.add(f"https://{project}")
    return frozenset(origins)


def _default_hosts() -> frozenset[str]:
    hosts = {
        "localhost",
        "127.0.0.1",
        "testserver",
        "*.vercel.app",
        "*.vercel.app.",
    }
    for key in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
        raw = (os.getenv(key) or "").strip()
        if raw:
            hosts.add(raw.split(":")[0])
    return frozenset(hosts)


@dataclass(frozen=True)
class Settings:
    falkor_host: str = os.getenv("FALKOR_HOST", "localhost")
    falkor_port: int = int(os.getenv("FALKOR_PORT", "6379"))
    falkor_username: str | None = os.getenv("FALKOR_USERNAME") or None
    falkor_password: str | None = os.getenv("FALKOR_PASSWORD") or None
    falkor_ssl: bool = _bool("FALKOR_SSL", False)
    tenant_id: str = os.getenv("SALUS_TENANT", "acme")
    graph_prefix: str = "salus"

    # Security
    api_key: str = field(default_factory=_api_key)
    admin_key: str | None = os.getenv("SALUS_ADMIN_KEY") or None
    auth_disabled: bool = _bool("SALUS_AUTH_DISABLED", False)
    cors_origins: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_CORS_ORIGINS") or _default_cors()
    )
    allowed_hosts: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_ALLOWED_HOSTS") or _default_hosts()
    )
    allowed_tenants: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_ALLOWED_TENANTS")
    )
    max_question_chars: int = int(os.getenv("SALUS_MAX_QUESTION_CHARS", "2000"))
    trust_x_forwarded_for: bool = _bool("SALUS_TRUST_XFF", False) or _on_vercel()
    hsts_enabled: bool = _bool("SALUS_HSTS", False)
    debug: bool = _bool("SALUS_DEBUG", False)
    env: str = os.getenv("SALUS_ENV") or (
        "production" if _on_vercel() and os.getenv("VERCEL_ENV") == "production" else "development"
    )
    on_vercel: bool = field(default_factory=_on_vercel)

    @property
    def graph_name(self) -> str:
        return f"{self.graph_prefix}:{self.tenant_id}"

    @property
    def is_production(self) -> bool:
        return self.env.strip().lower() == "production"


settings = Settings()

# Refuse insecure production defaults (skip hard crash on Vercel so /api/health can report)
if settings.is_production and not settings.on_vercel:
    if settings.auth_disabled:
        raise RuntimeError("SALUS_AUTH_DISABLED cannot be true in production")
    if settings.api_key in {"", "salus-dev-change-me"}:
        raise RuntimeError("Set a strong SALUS_API_KEY before running in production")
    if settings.debug:
        raise RuntimeError("SALUS_DEBUG cannot be true in production")
