"""Graph tools used by agents and exposed over MCP."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from salus.graph import query


def _node_name(n: Any) -> str | None:
    if n is None:
        return None
    if hasattr(n, "properties"):
        props = n.properties
        return props.get("name") or props.get("key") or props.get("title") or props.get("id")
    if isinstance(n, dict):
        return n.get("name") or n.get("key") or n.get("title") or n.get("id")
    return str(n)


def blast_radius(system_name: str, max_hops: int = 3, tenant_id: str | None = None) -> dict[str, Any]:
    """Multi-hop DEPENDS_ON traversal — works for any industry system."""
    cypher = """
    MATCH (s:System {name: $name})
    OPTIONAL MATCH (s)-[d:DEPENDS_ON*1..$hops]->(down:System)
    OPTIONAL MATCH (up:System)-[u:DEPENDS_ON*1..$hops]->(s)
    OPTIONAL MATCH (proj:Project)-[:USES]->(s)
    RETURN s.name AS root, s.domain AS domain, s.criticality AS criticality,
           collect(DISTINCT down.name) AS depends_on,
           collect(DISTINCT up.name) AS depended_by,
           collect(DISTINCT proj.name) AS projects
    """
    # FalkorDB may not allow param in variable-length hops — inline safely
    hops = max(1, min(int(max_hops), 5))
    cypher = f"""
    MATCH (s:System {{name: $name}})
    OPTIONAL MATCH (s)-[:DEPENDS_ON*1..{hops}]->(down:System)
    OPTIONAL MATCH (up:System)-[:DEPENDS_ON*1..{hops}]->(s)
    OPTIONAL MATCH (proj:Project)-[:USES]->(s)
    RETURN s.name AS root, s.domain AS domain, s.criticality AS criticality,
           collect(DISTINCT down.name) AS depends_on,
           collect(DISTINCT up.name) AS depended_by,
           collect(DISTINCT proj.name) AS projects
    """
    rows = query(cypher, {"name": system_name}, readonly=True, tenant_id=tenant_id)
    if not rows:
        return {"found": False, "system": system_name}
    r = rows[0]
    return {
        "found": True,
        "system": r[0],
        "domain": r[1],
        "criticality": r[2],
        "depends_on": [x for x in (r[3] or []) if x],
        "depended_by": [x for x in (r[4] or []) if x],
        "projects": [x for x in (r[5] or []) if x],
        "cypher": cypher.strip(),
    }


def who_owns_and_knows(system_name: str, tenant_id: str | None = None) -> dict[str, Any]:
    cypher = """
    MATCH (s:System {name: $name})
    OPTIONAL MATCH (owner:Person)-[:OWNS]->(s)
    OPTIONAL MATCH (p:Person)-[:WORKS_ON]->(:Project)-[:USES]->(s)
    OPTIONAL MATCH (expert:Person)-[:KNOWS]->(sk:Skill)
      WHERE sk.domain = s.domain OR toLower(sk.name) CONTAINS toLower(s.domain)
    RETURN s.name, s.domain,
           collect(DISTINCT owner.name) AS owners,
           collect(DISTINCT p.name) AS project_people,
           collect(DISTINCT expert.name) AS domain_experts
    """
    rows = query(cypher, {"name": system_name}, readonly=True, tenant_id=tenant_id)
    if not rows:
        return {"found": False, "system": system_name}
    r = rows[0]
    return {
        "found": True,
        "system": r[0],
        "domain": r[1],
        "owners": [x for x in (r[2] or []) if x],
        "project_people": [x for x in (r[3] or []) if x],
        "domain_experts": [x for x in (r[4] or []) if x],
        "cypher": cypher.strip(),
    }


def recall_memory(about: str, limit: int = 5, tenant_id: str | None = None) -> dict[str, Any]:
    """Episodic + semantic memory for an entity name (system/person/project)."""
    lim = max(1, min(int(limit), 20))
    ep_cypher = f"""
    MATCH (ep:Episode)-[:ABOUT_ENTITY]->(n)
    WHERE n.name = $about OR n.key = $about OR n.id = $about
    RETURN ep.id, ep.summary, ep.at, ep.importance
    ORDER BY ep.importance DESC, ep.at DESC
    LIMIT {lim}
    """
    fact_cypher = f"""
    MATCH (f:Fact)-[:ABOUT_ENTITY]->(n)
    WHERE (n.name = $about OR n.key = $about OR n.id = $about)
      AND (f.valid_to IS NULL)
    RETURN f.id, f.statement, f.confidence, f.source
    ORDER BY f.confidence DESC
    LIMIT {lim}
    """
    episodes = [
        {"id": r[0], "summary": r[1], "at": r[2], "importance": r[3]}
        for r in query(ep_cypher, {"about": about}, readonly=True, tenant_id=tenant_id)
    ]
    facts = [
        {"id": r[0], "statement": r[1], "confidence": r[2], "source": r[3]}
        for r in query(fact_cypher, {"about": about}, readonly=True, tenant_id=tenant_id)
    ]
    return {"about": about, "episodes": episodes, "facts": facts}


def find_runbooks(system_name: str, tenant_id: str | None = None) -> dict[str, Any]:
    cypher = """
    MATCH (d:Document)-[:REFERENCES]->(s:System {name: $name})
    OPTIONAL MATCH (author:Person)-[:AUTHORED]->(d)
    RETURN d.title, d.url, d.domain, d.summary, collect(DISTINCT author.name) AS authors
    """
    docs = []
    for r in query(cypher, {"name": system_name}, readonly=True, tenant_id=tenant_id):
        docs.append(
            {
                "title": r[0],
                "url": r[1],
                "domain": r[2],
                "summary": r[3],
                "authors": [x for x in (r[4] or []) if x],
            }
        )
    return {"system": system_name, "documents": docs}


def list_systems(domain: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    if domain:
        cypher = """
        MATCH (s:System {domain: $domain})
        RETURN s.name, s.kind, s.criticality, s.domain
        ORDER BY s.criticality, s.name
        """
        rows = query(cypher, {"domain": domain}, readonly=True, tenant_id=tenant_id)
    else:
        cypher = """
        MATCH (s:System)
        RETURN s.name, s.kind, s.criticality, s.domain
        ORDER BY s.domain, s.name
        """
        rows = query(cypher, readonly=True, tenant_id=tenant_id)
    return {
        "systems": [
            {"name": r[0], "kind": r[1], "criticality": r[2], "domain": r[3]} for r in rows
        ]
    }


def shared_state(key: str = "active_incident", tenant_id: str | None = None) -> dict[str, Any]:
    cypher = """
    MATCH (st:SharedState {key: $key})
    OPTIONAL MATCH (ag:Agent)-[sh:SHARES]->(st)
    RETURN st.value_json, st.version, collect(ag.name + ':' + sh.mode)
    """
    rows = query(cypher, {"key": key}, readonly=True, tenant_id=tenant_id)
    if not rows:
        return {"found": False, "key": key}
    return {
        "found": True,
        "key": key,
        "value": json.loads(rows[0][0]) if rows[0][0] else None,
        "version": rows[0][1],
        "agents": rows[0][2],
    }


def record_investigation(
    *,
    system_name: str,
    question: str,
    tool_trace: list[dict[str, Any]],
    evidence_summary: str,
    confidence: float,
    action_kind: str,
    action_target: str | None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Persist Investigation + ToolCalls + EvidencePath + Action (Track 01 explainability)."""
    now = int(time.time())
    inv_id = f"inv:{uuid.uuid4().hex[:8]}"
    path_id = f"path:{uuid.uuid4().hex[:8]}"
    act_id = f"act:{uuid.uuid4().hex[:8]}"

    query(
        """
        MATCH (a_inv:Agent {role: 'investigator'})
        MATCH (a_actor:Agent {role: 'actor'})
        OPTIONAL MATCH (s:System {name: $system})
        OPTIONAL MATCH (owner:Person)-[:OWNS]->(s)
        CREATE (inv:Investigation {
          id: $inv_id, status: 'open', started_at: $now, closed_at: null,
          hypothesis: $question
        })
        CREATE (inv)-[:LED_BY]->(a_inv)
        CREATE (path:EvidencePath {
          id: $path_id, cypher: $path_cypher,
          node_ids: $node_ids, rel_types: ['DEPENDS_ON','OWNS','ABOUT_ENTITY'],
          summary: $summary, confidence: $confidence
        })
        CREATE (path)-[:SUPPORTS]->(inv)
        FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END |
          CREATE (path)-[:TOUCHES {hop: 0}]->(s)
        )
        CREATE (act:Action {
          id: $act_id, kind: $action_kind, status: 'proposed',
          params_json: $params, result_json: '{}', at: $now
        })
        CREATE (inv)-[:DECIDED]->(act)
        CREATE (act)-[:EXECUTED_BY]->(a_actor)
        CREATE (path)-[:SUPPORTS]->(act)
        FOREACH (o IN CASE WHEN owner IS NULL THEN [] ELSE [owner] END |
          CREATE (act)-[:AFFECTS]->(o)
        )
        RETURN inv.id, path.id, act.id, collect(DISTINCT owner.name)
        """,
        {
            "inv_id": inv_id,
            "path_id": path_id,
            "act_id": act_id,
            "now": now,
            "question": question,
            "system": system_name,
            "path_cypher": tool_trace[-1].get("cypher", "") if tool_trace else "",
            "node_ids": [system_name],
            "summary": evidence_summary,
            "confidence": confidence,
            "action_kind": action_kind,
            "params": json.dumps({"system": system_name, "target": action_target, "question": question}),
        },
        tenant_id=tenant_id,
    )

    # Log tool calls
    prev = None
    for i, step in enumerate(tool_trace, start=1):
        tc_id = f"tool:{uuid.uuid4().hex[:8]}"
        query(
            """
            MATCH (inv:Investigation {id: $inv_id})
            CREATE (tc:ToolCall {
              id: $tc_id, tool: $tool, args_json: $args,
              result_summary: $summary, at: $now, latency_ms: $latency
            })
            CREATE (inv)-[:QUERIED {step: $step}]->(tc)
            RETURN tc.id
            """,
            {
                "inv_id": inv_id,
                "tc_id": tc_id,
                "tool": step.get("tool", "unknown"),
                "args": json.dumps(step.get("args", {})),
                "summary": str(step.get("result_summary", ""))[:500],
                "now": now + i,
                "latency": step.get("latency_ms", 0),
                "step": i,
            },
            tenant_id=tenant_id,
        )
        if prev:
            query(
                """
                MATCH (a:ToolCall {id: $a}), (b:ToolCall {id: $b})
                CREATE (a)-[:NEXT]->(b)
                """,
                {"a": prev, "b": tc_id},
                tenant_id=tenant_id,
            )
        prev = tc_id

    return {
        "investigation_id": inv_id,
        "evidence_path_id": path_id,
        "action_id": act_id,
        "action_kind": action_kind,
        "action_target": action_target,
    }


def extract_system_mention(text: str, tenant_id: str | None = None) -> str | None:
    systems = list_systems(tenant_id=tenant_id)["systems"]
    lower = text.lower()
    # Prefer longer names first
    names = sorted((s["name"] for s in systems), key=len, reverse=True)
    for name in names:
        if name.lower() in lower:
            return name
    # Domain keyword heuristics → primary system
    heuristics = {
        "checkout": "payments-api",
        "payment": "payments-api",
        "decline": "payments-api",
        "fraud": "risk-engine",
        "ehr": "ehr-core",
        "patient": "ehr-core",
        "hospital": "ehr-core",
        "badge": "badge-controller",
        "access": "badge-controller",
        "door": "badge-controller",
        "camera": "camera-nvr",
        "hvac": "hvac-wing-b",
        "cooling": "hvac-wing-b",
        "ac ": "hvac-wing-b",
        "air condition": "hvac-wing-b",
        "wing b": "hvac-wing-b",
        "temperature": "hvac-wing-b",
    }
    for key, sys_name in heuristics.items():
        if key in lower:
            return sys_name
    return None
