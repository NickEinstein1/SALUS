"""Track 03 — company brain: decisions, sources, knowledge currency, ingest helpers."""

from __future__ import annotations

import time
import uuid
from typing import Any

from salus.graph import query


def trace_decisions(system_name: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Trace decisions for a system back to authors, projects, and superseded history."""
    cypher = """
    MATCH (s:System {name: $name})
    OPTIONAL MATCH (d:Decision)-[:REFERENCES]->(s)
    OPTIONAL MATCH (d)-[:DECIDED_FOR]->(proj:Project)
    OPTIONAL MATCH (author:Person)-[:AUTHORED]->(d)
    OPTIONAL MATCH (d)-[:SUPERSEDES]->(old:Decision)
    OPTIONAL MATCH (newer:Decision)-[:SUPERSEDES]->(d)
    RETURN d.id, d.title, d.status, d.rationale, d.domain, d.decided_at,
           collect(DISTINCT author.name) AS authors,
           collect(DISTINCT proj.name) AS projects,
           collect(DISTINCT old.title) AS superseded,
           collect(DISTINCT newer.title) AS superseded_by
    """
    rows = query(cypher, {"name": system_name}, readonly=True, tenant_id=tenant_id)
    decisions = []
    for r in rows:
        if not r[0]:
            continue
        decisions.append(
            {
                "id": r[0],
                "title": r[1],
                "status": r[2],
                "rationale": r[3],
                "domain": r[4],
                "decided_at": r[5],
                "authors": [x for x in (r[6] or []) if x],
                "projects": [x for x in (r[7] or []) if x],
                "superseded": [x for x in (r[8] or []) if x],
                "superseded_by": [x for x in (r[9] or []) if x],
            }
        )
    return {"system": system_name, "decisions": decisions, "cypher": cypher.strip()}


def invalidate_fact(
    fact_id: str,
    *,
    reason: str,
    replacement_statement: str | None = None,
    about_system: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Keep knowledge current: set valid_to and optionally create replacement + INVALIDATES."""
    now = int(time.time())
    query(
        """
        MATCH (old:Fact {id: $fid})
        SET old.valid_to = $now
        RETURN old.id
        """,
        {"fid": fact_id, "now": now},
        tenant_id=tenant_id,
    )
    new_id = None
    if replacement_statement:
        new_id = f"fact:{uuid.uuid4().hex[:8]}"
        query(
            """
            MATCH (old:Fact {id: $old})
            OPTIONAL MATCH (sys:System {name: $system})
            CREATE (neu:Fact {
              id: $new, statement: $stmt, confidence: 0.85,
              valid_from: $now, valid_to: null, source: $reason
            })
            CREATE (neu)-[:INVALIDATES {at: $now, reason: $reason}]->(old)
            FOREACH (_ IN CASE WHEN sys IS NULL THEN [] ELSE [1] END |
              CREATE (neu)-[:ABOUT_ENTITY]->(sys)
            )
            RETURN neu.id
            """,
            {
                "old": fact_id,
                "new": new_id,
                "stmt": replacement_statement,
                "now": now,
                "reason": reason,
                "system": about_system,
            },
            tenant_id=tenant_id,
        )
    return {"invalidated": fact_id, "replacement": new_id, "at": now, "reason": reason}


def supersede_decision(
    old_decision_id: str,
    *,
    title: str,
    rationale: str,
    author_person_id: str | None = None,
    domain: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    new_id = f"dec:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (old:Decision {id: $old})
        SET old.status = 'superseded'
        CREATE (neu:Decision {
          id: $new, title: $title, status: 'accepted',
          domain: coalesce($domain, old.domain),
          decided_at: $now, rationale: $rationale
        })
        CREATE (neu)-[:SUPERSEDES {at: $now}]->(old)
        RETURN neu.id
        """,
        {
            "old": old_decision_id,
            "new": new_id,
            "title": title,
            "rationale": rationale,
            "domain": domain,
            "now": now,
        },
        tenant_id=tenant_id,
    )
    if author_person_id:
        query(
            """
            MATCH (p:Person {id: $pid}), (d:Decision {id: $did})
            CREATE (p)-[:AUTHORED {at: $now}]->(d)
            """,
            {"pid": author_person_id, "did": new_id, "now": now},
            tenant_id=tenant_id,
        )
    return {"new_decision_id": new_id, "supersedes": old_decision_id}


def collect_sources(system_name: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Aggregate clear sources: docs, decisions, tickets, episodes, facts."""
    docs = query(
        """
        MATCH (d:Document)-[:REFERENCES]->(s:System {name: $name})
        RETURN d.title, d.url, d.domain, d.summary
        """,
        {"name": system_name},
        readonly=True,
        tenant_id=tenant_id,
    )
    tickets = query(
        """
        MATCH (t:Ticket)-[:ABOUT]->(s:System {name: $name})
        RETURN t.key, t.title, t.status, t.severity, t.domain
        """,
        {"name": system_name},
        readonly=True,
        tenant_id=tenant_id,
    )
    chats = query(
        """
        MATCH (m:Message)-[:MENTIONS]->(s:System {name: $name})
        RETURN m.id, m.role, m.content, m.at
        ORDER BY m.at DESC LIMIT 10
        """,
        {"name": system_name},
        readonly=True,
        tenant_id=tenant_id,
    )
    return {
        "system": system_name,
        "documents": [
            {"title": r[0], "url": r[1], "domain": r[2], "summary": r[3]} for r in docs
        ],
        "tickets": [
            {"key": r[0], "title": r[1], "status": r[2], "severity": r[3], "domain": r[4]}
            for r in tickets
        ],
        "chats": [
            {"id": r[0], "role": r[1], "content": r[2], "at": r[3]} for r in chats
        ],
    }
