"""Track 01 — actions that mutate the graph based on investigation evidence."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from salus.graph import query


def page_owner(
    person_name: str,
    *,
    ticket_key: str | None = None,
    system_name: str | None = None,
    reason: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (actor:Agent {role: 'actor'})
        MATCH (p:Person {name: $name})
        OPTIONAL MATCH (t:Ticket {key: $ticket})
        OPTIONAL MATCH (s:System {name: $system})
        CREATE (a:Action {
          id: $aid, kind: 'page_owner', status: 'completed',
          params_json: $params, result_json: $result, at: $now
        })
        CREATE (a)-[:EXECUTED_BY]->(actor)
        CREATE (a)-[:AFFECTS]->(p)
        FOREACH (_ IN CASE WHEN t IS NULL THEN [] ELSE [1] END | CREATE (a)-[:AFFECTS]->(t))
        FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | CREATE (a)-[:AFFECTS]->(s))
        FOREACH (_ IN CASE WHEN t IS NULL THEN [] ELSE [1] END |
          SET t.status = 'investigating'
        )
        RETURN a.id, p.email
        """,
        {
            "name": person_name,
            "ticket": ticket_key,
            "system": system_name,
            "aid": act_id,
            "params": json.dumps({"person": person_name, "reason": reason}),
            "result": json.dumps({"paged": True, "channel": "pager"}),
            "now": now,
        },
        tenant_id=tenant_id,
    )
    return {"action_id": act_id, "kind": "page_owner", "person": person_name, "status": "completed"}


def assign_ticket(
    ticket_key: str,
    person_name: str,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (actor:Agent {role: 'actor'})
        MATCH (t:Ticket {key: $key}), (p:Person {name: $name})
        CREATE (a:Action {
          id: $aid, kind: 'assign_ticket', status: 'completed',
          params_json: $params, result_json: '{"assigned":true}', at: $now
        })
        CREATE (a)-[:EXECUTED_BY]->(actor)
        CREATE (a)-[:AFFECTS]->(t)
        CREATE (a)-[:AFFECTS]->(p)
        CREATE (t)-[:ASSIGNED_TO {at: $now}]->(p)
        SET t.status = 'assigned'
        RETURN a.id
        """,
        {
            "key": ticket_key,
            "name": person_name,
            "aid": act_id,
            "params": json.dumps({"ticket": ticket_key, "person": person_name}),
            "now": now,
        },
        tenant_id=tenant_id,
    )
    return {"action_id": act_id, "kind": "assign_ticket", "ticket": ticket_key, "person": person_name}


def open_ticket_from_finding(
    *,
    title: str,
    system_name: str,
    severity: str = "SEV-2",
    domain: str | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    key = f"INC-{uuid.uuid4().hex[:4].upper()}"
    tid = f"tkt:{uuid.uuid4().hex[:8]}"
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (actor:Agent {role: 'actor'})
        MATCH (s:System {name: $system})
        CREATE (t:Ticket {
          id: $tid, key: $key, title: $title, status: 'open',
          severity: $severity, domain: coalesce($domain, s.domain), created_at: $now
        })
        CREATE (t)-[:ABOUT]->(s)
        CREATE (a:Action {
          id: $aid, kind: 'open_ticket', status: 'completed',
          params_json: $params, result_json: $result, at: $now
        })
        CREATE (a)-[:EXECUTED_BY]->(actor)
        CREATE (a)-[:AFFECTS]->(t)
        CREATE (a)-[:AFFECTS]->(s)
        RETURN t.key, a.id
        """,
        {
            "system": system_name,
            "tid": tid,
            "key": key,
            "title": title,
            "severity": severity,
            "domain": domain,
            "aid": act_id,
            "params": json.dumps({"title": title, "system": system_name}),
            "result": json.dumps({"ticket": key}),
            "now": now,
        },
        tenant_id=tenant_id,
    )
    return {"action_id": act_id, "kind": "open_ticket", "ticket_key": key}
