"""SALUS configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    falkor_host: str = os.getenv("FALKOR_HOST", "localhost")
    falkor_port: int = int(os.getenv("FALKOR_PORT", "6379"))
    falkor_password: str | None = os.getenv("FALKOR_PASSWORD") or None
    tenant_id: str = os.getenv("SALUS_TENANT", "acme")
    graph_prefix: str = "salus"

    @property
    def graph_name(self) -> str:
        return f"{self.graph_prefix}:{self.tenant_id}"


settings = Settings()
