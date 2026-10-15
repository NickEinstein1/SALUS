"""Track 03 — ingest docs, tickets, and chats into the same company graph."""

from __future__ import annotations

import time
import uuid
from typing import Any

from salus.graph import query


def ingest_document(
    *,
    title: str,
    summary: str,
    url: str | None = None,
    domain: str = "ops",
    source: str = "upload",
    references_systems: list[str] | None = None,
    author_email: str | None = None,
    channel: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    doc_id = f"doc:{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    query(
        """
        CREATE (d:Document {
          id: $id, title: $title, source: $source, url: $url,
          domain: $domain, updated_at: $now, summary: $summary
        })
        RETURN d.id
        """,
        {
            "id": doc_id,
            "title": title,
            "source": source,
            "url": url or "",
            "domain": domain,
            "now": now,
            "summary": summary,
        },
        tenant_id=tenant_id,
    )
    for sys_name in references_systems or []:
        query(
            """
            MATCH (d:Document {id: $did}), (s:System {name: $name})
            CREATE (d)-[:REFERENCES]->(s)
            """,
            {"did": doc_id, "name": sys_name},
            tenant_id=tenant_id,
        )
    if author_email:
        query(
            """
            MATCH (d:Document {id: $did}), (p:Person {email: $email})
            CREATE (p)-[:AUTHORED {at: $now}]->(d)
            """,
            {"did": doc_id, "email": author_email, "now": now},
            tenant_id=tenant_id,
        )
    if channel:
        existing = query(
            "MATCH (c:Channel {name: $channel}) RETURN c.id LIMIT 1",
            {"channel": channel},
            readonly=True,
            tenant_id=tenant_id,
        )
        cid = existing[0][0] if existing else f"chan:{uuid.uuid4().hex[:6]}"
        if not existing:
            query(
                "CREATE (:Channel {id: $cid, name: $channel, platform: 'ingest'})",
                {"cid": cid, "channel": channel},
                tenant_id=tenant_id,
            )
        query(
            """
            MATCH (d:Document {id: $did}), (c:Channel {id: $cid})
            CREATE (d)-[:POSTED_IN]->(c)
            """,
            {"did": doc_id, "cid": cid},
            tenant_id=tenant_id,
        )
    return {"document_id": doc_id, "title": title}


def ingest_ticket(
    *,
    key: str,
    title: str,
    severity: str = "SEV-3",
    domain: str = "ops",
    about_systems: list[str] | None = None,
    assignee_email: str | None = None,
    channel: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    tid = f"tkt:{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    query(
        """
        CREATE (t:Ticket {
          id: $id, key: $key, title: $title, status: 'open',
          severity: $severity, domain: $domain, created_at: $now
        })
        RETURN t.id
        """,
        {
            "id": tid,
            "key": key,
            "title": title,
            "severity": severity,
            "domain": domain,
            "now": now,
        },
        tenant_id=tenant_id,
    )
    for sys_name in about_systems or []:
        query(
            """
            MATCH (t:Ticket {id: $tid}), (s:System {name: $name})
            CREATE (t)-[:ABOUT]->(s)
            """,
            {"tid": tid, "name": sys_name},
            tenant_id=tenant_id,
        )
    if assignee_email:
        query(
            """
            MATCH (t:Ticket {id: $tid}), (p:Person {email: $email})
            CREATE (t)-[:ASSIGNED_TO {at: $now}]->(p)
            """,
            {"tid": tid, "email": assignee_email, "now": now},
            tenant_id=tenant_id,
        )
    if channel:
        _link_channel("Ticket", tid, channel, tenant_id)
    return {"ticket_id": tid, "key": key}


def _link_channel(label: str, node_id: str, channel: str, tenant_id: str | None) -> None:
    existing = query(
        "MATCH (c:Channel {name: $channel}) RETURN c.id LIMIT 1",
        {"channel": channel},
        readonly=True,
        tenant_id=tenant_id,
    )
    cid = existing[0][0] if existing else f"chan:{uuid.uuid4().hex[:6]}"
    if not existing:
        query(
            "CREATE (:Channel {id: $cid, name: $channel, platform: 'ingest'})",
            {"cid": cid, "channel": channel},
            tenant_id=tenant_id,
        )
    query(
        f"""
        MATCH (n:{label} {{id: $nid}}), (c:Channel {{id: $cid}})
        CREATE (n)-[:POSTED_IN]->(c)
        """,
        {"nid": node_id, "cid": cid},
        tenant_id=tenant_id,
    )


def ingest_chat(
    *,
    content: str,
    role: str = "user",
    user_id: str,
    mention_systems: list[str] | None = None,
    session_id: str | None = None,
    channel: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Ingest a chat message into the company graph (and optional session)."""
    from salus import memory

    if not session_id:
        sess = memory.get_or_create_session(user_id, tenant_id=tenant_id)
        session_id = sess["session_id"]
    msg = memory.append_message(
        session_id, role, content, sender_id=user_id, tenant_id=tenant_id
    )
    for sys_name in mention_systems or []:
        query(
            """
            MATCH (m:Message {id: $mid}), (s:System {name: $name})
            CREATE (m)-[:MENTIONS]->(s)
            """,
            {"mid": msg["message_id"], "name": sys_name},
            tenant_id=tenant_id,
        )
    if channel:
        _link_channel("Message", msg["message_id"], channel, tenant_id)
    return {"message_id": msg["message_id"], "session_id": session_id, "seq": msg["seq"]}
