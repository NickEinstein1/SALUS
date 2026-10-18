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


def _api_key() -> str:
    env = os.getenv("SALUS_API_KEY", "").strip()
    if env:
        return env
    # Stable-enough local default so UI can work; override in production.
    return "salus-dev-change-me"


@dataclass(frozen=True)
class Settings:
    falkor_host: str = os.getenv("FALKOR_HOST", "localhost")
    falkor_port: int = int(os.getenv("FALKOR_PORT", "6379"))
    falkor_password: str | None = os.getenv("FALKOR_PASSWORD") or None
    tenant_id: str = os.getenv("SALUS_TENANT", "acme")
    graph_prefix: str = "salus"

    # Security
    api_key: str = field(default_factory=_api_key)
    admin_key: str | None = os.getenv("SALUS_ADMIN_KEY") or None
    auth_disabled: bool = _bool("SALUS_AUTH_DISABLED", False)
    cors_origins: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_CORS_ORIGINS")
        or frozenset({"http://127.0.0.1:8080", "http://localhost:8080"})
    )
    allowed_hosts: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_ALLOWED_HOSTS")
        or frozenset(
            {
                "localhost",
                "127.0.0.1",
                "testserver",
                "*.vercel.app",
                "*.vercel.app.",  # Host header sometimes has trailing dot
            }
        )
    )
    allowed_tenants: frozenset[str] = field(
        default_factory=lambda: _csv("SALUS_ALLOWED_TENANTS")
    )
    max_question_chars: int = int(os.getenv("SALUS_MAX_QUESTION_CHARS", "2000"))
    trust_x_forwarded_for: bool = _bool("SALUS_TRUST_XFF", False)
    hsts_enabled: bool = _bool("SALUS_HSTS", False)
    debug: bool = _bool("SALUS_DEBUG", False)
    env: str = os.getenv("SALUS_ENV", "development")

    @property
    def graph_name(self) -> str:
        return f"{self.graph_prefix}:{self.tenant_id}"

    @property
    def is_production(self) -> bool:
        return self.env.strip().lower() == "production"


settings = Settings()

# Refuse insecure production defaults
if settings.is_production:
    if settings.auth_disabled:
        raise RuntimeError("SALUS_AUTH_DISABLED cannot be true in production")
    if settings.api_key in {"", "salus-dev-change-me"}:
        raise RuntimeError("Set a strong SALUS_API_KEY before running in production")
    if settings.debug:
        raise RuntimeError("SALUS_DEBUG cannot be true in production")
