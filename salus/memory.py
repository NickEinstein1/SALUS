"""Track 02 — episodic/semantic/procedural memory, sessions, shared state, per-user isolation."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from salus.graph import query


def get_or_create_session(
    user_id: str,
    tenant_id: str | None = None,
    *,
    continue_previous: bool = True,
) -> dict[str, Any]:
    """Per-user session with optional CONTINUES link to prior open/closed session."""
    now = int(time.time())
    # Close look: find most recent session for this user
    prev = query(
        """
        MATCH (s:Session {user_id: $user_id})
        RETURN s.id, s.status
        ORDER BY s.started_at DESC
        LIMIT 1
        """,
        {"user_id": user_id},
        readonly=True,
        tenant_id=tenant_id,
    )
    sid = f"sess:{user_id}:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (t:Tenant)
        CREATE (s:Session {
          id: $sid, user_id: $user_id, started_at: $now, ended_at: null, status: 'open'
        })
        CREATE (s)-[:FOR_TENANT]->(t)
        RETURN s.id
        """,
        {"sid": sid, "user_id": user_id, "now": now},
        tenant_id=tenant_id,
    )
    continued_from = None
    if continue_previous and prev:
        continued_from = prev[0][0]
        query(
            """
            MATCH (curr:Session {id: $curr}), (prev:Session {id: $prev})
            CREATE (curr)-[:CONTINUES]->(prev)
            """,
            {"curr": sid, "prev": continued_from},
            tenant_id=tenant_id,
        )
    return {"session_id": sid, "user_id": user_id, "continues": continued_from}


def append_message(
    session_id: str,
    role: str,
    content: str,
    sender_id: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    mid = f"msg:{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    seq_rows = query(
        """
        MATCH (:Message)-[r:IN_SESSION]->(:Session {id: $sid})
        RETURN coalesce(max(r.seq), 0)
        """,
        {"sid": session_id},
        readonly=True,
        tenant_id=tenant_id,
    )
    seq = int(seq_rows[0][0]) + 1 if seq_rows else 1
    query(
        """
        MATCH (s:Session {id: $sid})
        CREATE (m:Message {
          id: $mid, role: $role, content: $content, at: $now, token_count: $tokens
        })
        CREATE (m)-[:IN_SESSION {seq: $seq}]->(s)
        RETURN m.id
        """,
        {
            "sid": session_id,
            "mid": mid,
            "role": role,
            "content": content,
            "now": now,
            "tokens": len(content.split()),
            "seq": seq,
        },
        tenant_id=tenant_id,
    )
    if sender_id:
        query(
            """
            MATCH (m:Message {id: $mid})
            OPTIONAL MATCH (p:Person {id: $sender})
            OPTIONAL MATCH (a:Agent {id: $sender})
            WITH m, coalesce(p, a) AS who
            FOREACH (_ IN CASE WHEN who IS NULL THEN [] ELSE [1] END |
              CREATE (m)-[:SENT_BY]->(who)
            )
            """,
            {"mid": mid, "sender": sender_id},
            tenant_id=tenant_id,
        )
    return {"message_id": mid, "seq": seq}


def session_history(session_id: str, tenant_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    lim = max(1, min(int(limit), 200))
    rows = query(
        f"""
        MATCH (m:Message)-[r:IN_SESSION]->(s:Session {{id: $sid}})
        RETURN r.seq, m.role, m.content, m.at
        ORDER BY r.seq
        LIMIT {lim}
        """,
        {"sid": session_id},
        readonly=True,
        tenant_id=tenant_id,
    )
    return [{"seq": r[0], "role": r[1], "content": r[2], "at": r[3]} for r in rows]


def cross_session_memory(user_id: str, tenant_id: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Recall episodes remembered by any of this user's sessions (per-user isolation)."""
    lim = max(1, min(int(limit), 50))
    rows = query(
        f"""
        MATCH (s:Session {{user_id: $user_id}})-[:REMEMBERS]->(ep:Episode)
        RETURN DISTINCT ep.id, ep.summary, ep.at, ep.importance
        ORDER BY ep.at DESC
        LIMIT {lim}
        """,
        {"user_id": user_id},
        readonly=True,
        tenant_id=tenant_id,
    )
    # Also pull messages from continued chain
    msgs = query(
        f"""
        MATCH (s:Session {{user_id: $user_id}})<-[:IN_SESSION]-(m:Message)
        RETURN m.role, m.content, m.at
        ORDER BY m.at DESC
        LIMIT {lim}
        """,
        {"user_id": user_id},
        readonly=True,
        tenant_id=tenant_id,
    )
    return {
        "user_id": user_id,
        "episodes": [{"id": r[0], "summary": r[1], "at": r[2], "importance": r[3]} for r in rows],
        "recent_messages": [{"role": r[0], "content": r[1], "at": r[2]} for r in msgs],
    }


def load_procedure(name: str | None = None, tenant_id: str | None = None) -> dict[str, Any] | None:
    if name:
        rows = query(
            """
            MATCH (p:Procedure {name: $name})
            RETURN p.id, p.name, p.steps_json, p.success_rate
            LIMIT 1
            """,
            {"name": name},
            readonly=True,
            tenant_id=tenant_id,
        )
    else:
        rows = query(
            """
            MATCH (p:Procedure)
            RETURN p.id, p.name, p.steps_json, p.success_rate
            ORDER BY p.success_rate DESC
            LIMIT 1
            """,
            readonly=True,
            tenant_id=tenant_id,
        )
    if not rows:
        return None
    r = rows[0]
    try:
        steps = json.loads(r[2]) if isinstance(r[2], str) else r[2]
    except json.JSONDecodeError:
        steps = [r[2]]
    return {"id": r[0], "name": r[1], "steps": steps, "success_rate": r[3]}


def mark_procedure_used(agent_role: str, procedure_id: str, tenant_id: str | None = None) -> None:
    query(
        """
        MATCH (a:Agent {role: $role}), (p:Procedure {id: $pid})
        MERGE (a)-[:USES_PROCEDURE]->(p)
        """,
        {"role": agent_role, "pid": procedure_id},
        tenant_id=tenant_id,
    )


def write_episode(
    summary: str,
    *,
    system: str | None = None,
    session_id: str | None = None,
    importance: float = 0.7,
    tenant_id: str | None = None,
) -> str:
    eid = f"ep:{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    query(
        """
        OPTIONAL MATCH (sys:System {name: $system})
        CREATE (ep:Episode {id: $eid, summary: $summary, at: $now, importance: $importance})
        FOREACH (_ IN CASE WHEN sys IS NULL THEN [] ELSE [1] END |
          CREATE (ep)-[:ABOUT_ENTITY]->(sys)
        )
        RETURN ep.id
        """,
        {
            "eid": eid,
            "summary": summary,
            "system": system,
            "now": now,
            "importance": importance,
        },
        tenant_id=tenant_id,
    )
    if session_id:
        query(
            """
            MATCH (s:Session {id: $sid}), (ep:Episode {id: $eid})
            CREATE (s)-[:REMEMBERS]->(ep)
            """,
            {"sid": session_id, "eid": eid},
            tenant_id=tenant_id,
        )
    return eid


def write_fact(
    statement: str,
    *,
    about_system: str | None = None,
    confidence: float = 0.8,
    source: str = "salus",
    tenant_id: str | None = None,
) -> str:
    fid = f"fact:{uuid.uuid4().hex[:8]}"
    now = int(time.time())
    query(
        """
        OPTIONAL MATCH (sys:System {name: $system})
        CREATE (f:Fact {
          id: $fid, statement: $statement, confidence: $confidence,
          valid_from: $now, valid_to: null, source: $source
        })
        FOREACH (_ IN CASE WHEN sys IS NULL THEN [] ELSE [1] END |
          CREATE (f)-[:ABOUT_ENTITY]->(sys)
        )
        RETURN f.id
        """,
        {
            "fid": fid,
            "statement": statement,
            "confidence": confidence,
            "now": now,
            "source": source,
            "system": about_system,
        },
        tenant_id=tenant_id,
    )
    return fid


def read_shared_state(key: str = "active_incident", tenant_id: str | None = None) -> dict[str, Any]:
    rows = query(
        """
        MATCH (st:SharedState {key: $key})
        RETURN st.id, st.value_json, st.version, st.updated_at
        """,
        {"key": key},
        readonly=True,
        tenant_id=tenant_id,
    )
    if not rows:
        return {"found": False, "key": key}
    return {
        "found": True,
        "id": rows[0][0],
        "key": key,
        "value": json.loads(rows[0][1]) if rows[0][1] else {},
        "version": rows[0][2],
        "updated_at": rows[0][3],
    }


def cas_shared_state(
    key: str,
    expected_version: int,
    new_value: dict[str, Any],
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Optimistic concurrency control for high-concurrency shared writes."""
    now = int(time.time())
    payload = json.dumps(new_value)
    rows = query(
        """
        MATCH (st:SharedState {key: $key})
        WHERE st.version = $expected
        SET st.value_json = $payload, st.version = st.version + 1, st.updated_at = $now
        RETURN st.version, st.value_json
        """,
        {"key": key, "expected": expected_version, "payload": payload, "now": now},
        tenant_id=tenant_id,
    )
    if not rows:
        current = read_shared_state(key, tenant_id=tenant_id)
        return {
            "ok": False,
            "conflict": True,
            "expected_version": expected_version,
            "current": current,
        }
    return {
        "ok": True,
        "conflict": False,
        "version": rows[0][0],
        "value": json.loads(rows[0][1]),
    }


def update_shared_state_with_retry(
    key: str,
    mutator,
    tenant_id: str | None = None,
    retries: int = 8,
) -> dict[str, Any]:
    """Retry loop demonstrating concurrent-safe shared state updates."""
    last: dict[str, Any] = {}
    for _ in range(retries):
        cur = read_shared_state(key, tenant_id=tenant_id)
        if not cur.get("found"):
            # create
            sid = f"state:{uuid.uuid4().hex[:8]}"
            query(
                """
                CREATE (st:SharedState {
                  id: $id, key: $key, value_json: $val, version: 1, updated_at: $now
                })
                """,
                {
                    "id": sid,
                    "key": key,
                    "val": json.dumps(mutator({})),
                    "now": int(time.time()),
                },
                tenant_id=tenant_id,
            )
            return read_shared_state(key, tenant_id=tenant_id)
        new_val = mutator(dict(cur.get("value") or {}))
        last = cas_shared_state(key, int(cur["version"]), new_val, tenant_id=tenant_id)
        if last.get("ok"):
            return last
    return last
