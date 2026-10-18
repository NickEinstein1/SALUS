"""FalkorDB client helpers for SALUS."""

from __future__ import annotations

from typing import Any

from falkordb import FalkorDB

from salus.config import Settings, settings


def connect(cfg: Settings | None = None) -> FalkorDB:
    cfg = cfg or settings
    kwargs: dict[str, Any] = {"host": cfg.falkor_host, "port": cfg.falkor_port}
    if cfg.falkor_username:
        kwargs["username"] = cfg.falkor_username
    if cfg.falkor_password:
        kwargs["password"] = cfg.falkor_password
    if cfg.falkor_ssl:
        kwargs["ssl"] = True
    return FalkorDB(**kwargs)


def select_graph(tenant_id: str | None = None, cfg: Settings | None = None):
    cfg = cfg or settings
    client = connect(cfg)
    name = f"{cfg.graph_prefix}:{tenant_id or cfg.tenant_id}"
    return client.select_graph(name)


def query(cypher: str, params: dict[str, Any] | None = None, *, readonly: bool = False, tenant_id: str | None = None):
    graph = select_graph(tenant_id)
    if readonly:
        result = graph.ro_query(cypher, params or {})
    else:
        result = graph.query(cypher, params or {})
    return result.result_set


def rows_as_dicts(result_set: list, columns: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in result_set:
        out.append({col: row[i] if i < len(row) else None for i, col in enumerate(columns)})
    return out


INDEX_STATEMENTS = [
    "CREATE INDEX FOR (n:Tenant) ON (n.id)",
    "CREATE INDEX FOR (n:Person) ON (n.id)",
    "CREATE INDEX FOR (n:Person) ON (n.email)",
    "CREATE INDEX FOR (n:Team) ON (n.id)",
    "CREATE INDEX FOR (n:Project) ON (n.id)",
    "CREATE INDEX FOR (n:System) ON (n.id)",
    "CREATE INDEX FOR (n:System) ON (n.name)",
    "CREATE INDEX FOR (n:Document) ON (n.id)",
    "CREATE INDEX FOR (n:Ticket) ON (n.id)",
    "CREATE INDEX FOR (n:Ticket) ON (n.key)",
    "CREATE INDEX FOR (n:Decision) ON (n.id)",
    "CREATE INDEX FOR (n:Skill) ON (n.id)",
    "CREATE INDEX FOR (n:Skill) ON (n.name)",
    "CREATE INDEX FOR (n:Channel) ON (n.id)",
    "CREATE INDEX FOR (n:Agent) ON (n.id)",
    "CREATE INDEX FOR (n:Session) ON (n.id)",
    "CREATE INDEX FOR (n:Session) ON (n.user_id)",
    "CREATE INDEX FOR (n:Message) ON (n.id)",
    "CREATE INDEX FOR (n:Episode) ON (n.id)",
    "CREATE INDEX FOR (n:Fact) ON (n.id)",
    "CREATE INDEX FOR (n:Procedure) ON (n.id)",
    "CREATE INDEX FOR (n:Handoff) ON (n.id)",
    "CREATE INDEX FOR (n:SharedState) ON (n.id)",
    "CREATE INDEX FOR (n:SharedState) ON (n.key)",
    "CREATE INDEX FOR (n:Finding) ON (n.id)",
    "CREATE INDEX FOR (n:Investigation) ON (n.id)",
    "CREATE INDEX FOR (n:Action) ON (n.id)",
    "CREATE INDEX FOR (n:EvidencePath) ON (n.id)",
    "CREATE INDEX FOR (n:ToolCall) ON (n.id)",
]


def ensure_indexes(tenant_id: str | None = None) -> int:
    created = 0
    for stmt in INDEX_STATEMENTS:
        try:
            query(stmt, tenant_id=tenant_id)
            created += 1
        except Exception:
            # Index may already exist
            pass
    return created
