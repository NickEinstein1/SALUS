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


def escalate_severity(
    ticket_key: str,
    new_severity: str = "SEV-1",
    *,
    reason: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    query(
        """
        MATCH (actor:Agent {role: 'actor'})
        MATCH (t:Ticket {key: $key})
        WITH actor, t, t.severity AS old
        SET t.severity = $sev, t.status = 'escalated'
        CREATE (a:Action {
          id: $aid, kind: 'escalate_severity', status: 'completed',
          params_json: $params, result_json: $result, at: $now
        })
        CREATE (a)-[:EXECUTED_BY]->(actor)
        CREATE (a)-[:AFFECTS]->(t)
        RETURN a.id, old
        """,
        {
            "key": ticket_key,
            "sev": new_severity,
            "aid": act_id,
            "params": json.dumps({"ticket": ticket_key, "severity": new_severity, "reason": reason}),
            "result": json.dumps({"escalated": True, "severity": new_severity}),
            "now": now,
        },
        tenant_id=tenant_id,
    )
    return {
        "action_id": act_id,
        "kind": "escalate_severity",
        "ticket": ticket_key,
        "severity": new_severity,
        "status": "completed",
    }


def escalate_to_manager(
    person_name: str,
    *,
    system_name: str | None = None,
    reason: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Escalate along REPORTS_TO to the manager of the owner/expert."""
    now = int(time.time())
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    rows = query(
        """
        MATCH (p:Person {name: $name})-[:REPORTS_TO]->(mgr:Person)
        RETURN mgr.name, mgr.email, p.name
        LIMIT 1
        """,
        {"name": person_name},
        readonly=True,
        tenant_id=tenant_id,
    )
    if not rows:
        return {
            "action_id": None,
            "kind": "escalate_to_manager",
            "status": "failed",
            "error": f"No manager found for {person_name}",
        }
    mgr_name, mgr_email, owner = rows[0]
    query(
        """
        MATCH (actor:Agent {role: 'actor'})
        MATCH (mgr:Person {name: $mgr}), (owner:Person {name: $owner})
        OPTIONAL MATCH (s:System {name: $system})
        CREATE (a:Action {
          id: $aid, kind: 'escalate_to_manager', status: 'completed',
          params_json: $params, result_json: $result, at: $now
        })
        CREATE (a)-[:EXECUTED_BY]->(actor)
        CREATE (a)-[:AFFECTS]->(mgr)
        CREATE (a)-[:AFFECTS]->(owner)
        FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | CREATE (a)-[:AFFECTS]->(s))
        RETURN a.id
        """,
        {
            "mgr": mgr_name,
            "owner": owner,
            "system": system_name,
            "aid": act_id,
            "params": json.dumps(
                {"from": owner, "to": mgr_name, "system": system_name, "reason": reason}
            ),
            "result": json.dumps({"paged_manager": True, "manager": mgr_name, "email": mgr_email}),
            "now": now,
        },
        tenant_id=tenant_id,
    )
    return {
        "action_id": act_id,
        "kind": "escalate_to_manager",
        "from": owner,
        "manager": mgr_name,
        "manager_email": mgr_email,
        "status": "completed",
    }


def escalate_to_sre(
    *,
    system_name: str,
    reason: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    act_id = f"act:{uuid.uuid4().hex[:8]}"
    rows = query(
        """
        MATCH (p:Person)-[:MEMBER_OF]->(t:Team {id: 'team:sre'})
        RETURN p.name
        ORDER BY p.name
        LIMIT 1
        """,
        readonly=True,
        tenant_id=tenant_id,
    )
    sre = rows[0][0] if rows else None
    if not sre:
        return {"kind": "escalate_to_sre", "status": "failed", "error": "No SRE on team"}
    page = page_owner(
        sre,
        system_name=system_name,
        reason=reason or "Escalated to SRE",
        tenant_id=tenant_id,
    )
    query(
        """
        MATCH (actor:Agent {role: 'actor'}), (a:Action {id: $page_aid})
        SET a.kind = 'escalate_to_sre'
        RETURN a.id
        """,
        {"page_aid": page["action_id"]},
        tenant_id=tenant_id,
    )
    return {
        "action_id": page.get("action_id") or act_id,
        "kind": "escalate_to_sre",
        "person": sre,
        "system": system_name,
        "status": "completed",
        "at": now,
    }
