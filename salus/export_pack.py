"""Export investigation context: graph nodes, reports, evidence embeddings."""

from __future__ import annotations

import csv
import io
import json
import time
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from salus.graph import query
from salus.tools import blast_radius, who_owns_and_knows


def _graph_slice(system: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    if system:
        focus = query(
            """
            MATCH (s:System {name: $name})
            RETURN s.id AS id, s.name AS name, s.domain AS domain,
                   s.criticality AS criticality, s.kind AS kind
            """,
            {"name": system},
            readonly=True,
            tenant_id=tenant_id,
        )
        down = query(
            """
            MATCH (s:System {name: $name})-[:DEPENDS_ON*1..3]->(n:System)
            RETURN DISTINCT n.id AS id, n.name AS name, n.domain AS domain,
                   n.criticality AS criticality, n.kind AS kind
            """,
            {"name": system},
            readonly=True,
            tenant_id=tenant_id,
        )
        up = query(
            """
            MATCH (n:System)-[:DEPENDS_ON*1..3]->(s:System {name: $name})
            RETURN DISTINCT n.id AS id, n.name AS name, n.domain AS domain,
                   n.criticality AS criticality, n.kind AS kind
            """,
            {"name": system},
            readonly=True,
            tenant_id=tenant_id,
        )
        rows = list(focus) + list(down) + list(up)
    else:
        rows = query(
            """
            MATCH (s:System)
            RETURN s.id AS id, s.name AS name, s.domain AS domain,
                   s.criticality AS criticality, s.kind AS kind
            """,
            readonly=True,
            tenant_id=tenant_id,
        )

    nodes: list[dict[str, Any]] = []
    people: dict[str, dict[str, Any]] = {}
    system_names: list[str] = []
    seen_nodes: set[str] = set()
    for sid, name, domain, crit, kind in rows:
        if not name or name in seen_nodes:
            continue
        seen_nodes.add(name)
        system_names.append(name)
        nodes.append(
            {
                "id": sid or name,
                "name": name,
                "label": "System",
                "domain": domain,
                "criticality": crit,
                "kind": kind,
            }
        )

    own_detail = query(
        """
        MATCH (p:Person)-[:OWNS]->(s:System)
        RETURN p.id, p.name, p.role, s.name
        """,
        readonly=True,
        tenant_id=tenant_id,
    )
    name_set_preview = set(system_names)
    for pid, pname, role, sname in own_detail:
        if system and sname not in name_set_preview:
            continue
        if pid and pid not in people:
            people[pid] = {
                "id": pid,
                "name": pname,
                "label": "Person",
                "role": role,
            }

    for p in people.values():
        nodes.append(p)

    edge_rows = query(
        """
        MATCH (a:System)-[r:DEPENDS_ON]->(b:System)
        RETURN a.name, type(r), b.name, r.kind
        """,
        readonly=True,
        tenant_id=tenant_id,
    )
    own_rows = query(
        """
        MATCH (p:Person)-[:OWNS]->(s:System)
        RETURN p.id, 'OWNS', s.name
        """,
        readonly=True,
        tenant_id=tenant_id,
    )

    name_set = set(system_names)
    edges: list[dict[str, Any]] = []
    for a, rel, b, kind in edge_rows:
        if not system or a in name_set or b in name_set:
            edges.append({"source": a, "target": b, "type": rel, "kind": kind})
    for pid, rel, sname in own_rows:
        if not system or sname in name_set:
            edges.append({"source": pid, "target": sname, "type": rel, "kind": "owns"})

    return {"nodes": nodes, "edges": edges, "focus": system}


def export_graph_nodes_json(system: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
    payload = _graph_slice(system, tenant_id)
    payload["format"] = "salus.graph_nodes.v1"
    payload["exported_at"] = int(time.time())
    return payload


def export_graph_nodes_csv(system: str | None = None, tenant_id: str | None = None) -> str:
    payload = _graph_slice(system, tenant_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["entity", "id", "name", "label", "domain", "criticality", "kind", "role"])
    for n in payload["nodes"]:
        w.writerow(
            [
                "node",
                n.get("id"),
                n.get("name"),
                n.get("label"),
                n.get("domain", ""),
                n.get("criticality", ""),
                n.get("kind", ""),
                n.get("role", ""),
            ]
        )
    w.writerow([])
    w.writerow(["entity", "source", "type", "target", "kind"])
    for e in payload["edges"]:
        w.writerow(["edge", e["source"], e["type"], e["target"], e.get("kind", "")])
    return buf.getvalue()


def export_graphml(system: str | None = None, tenant_id: str | None = None) -> str:
    payload = _graph_slice(system, tenant_id)
    root = Element("graphml")
    root.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
    graph = SubElement(root, "graph", {"id": "salus", "edgedefault": "directed"})
    for n in payload["nodes"]:
        node = SubElement(graph, "node", {"id": str(n["id"])})
        data = SubElement(node, "data", {"key": "label"})
        data.text = str(n.get("name") or n["id"])
        for k in ("domain", "criticality", "kind", "role", "label"):
            if n.get(k) is not None:
                d = SubElement(node, "data", {"key": k})
                d.text = str(n[k])
    for i, e in enumerate(payload["edges"]):
        SubElement(
            graph,
            "edge",
            {
                "id": f"e{i}",
                "source": str(e["source"]),
                "target": str(e["target"]),
            },
        )
    return tostring(root, encoding="unicode")


def evidence_embedding(
    *,
    result: dict[str, Any],
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Portable 'embedding' of the investigation: graph neighborhood + path + memory + sources."""
    system = result.get("system")
    graph = _graph_slice(system, tenant_id) if system else {"nodes": [], "edges": []}
    radius = blast_radius(system, tenant_id=tenant_id) if system else {}
    owners = who_owns_and_knows(system, tenant_id=tenant_id) if system else {}

    # Simple numeric feature vector per system node for ML/export consumers
    vectors = []
    crit_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
    for n in graph.get("nodes", []):
        if n.get("label") != "System":
            continue
        deg = sum(1 for e in graph["edges"] if e["source"] == n["name"] or e["target"] == n["name"])
        vectors.append(
            {
                "id": n["name"],
                "vector": [
                    crit_map.get(str(n.get("criticality") or "").lower(), 0.4),
                    float(deg),
                    1.0 if n["name"] == system else 0.0,
                    float(result.get("confidence") or 0),
                ],
                "dims": ["criticality", "degree", "is_focus", "run_confidence"],
            }
        )

    return {
        "format": "salus.evidence_embedding.v1",
        "exported_at": int(time.time()),
        "question_context": {
            "system": system,
            "domain": result.get("domain"),
            "confidence": result.get("confidence"),
            "investigation_id": result.get("investigation_id"),
            "evidence_summary": result.get("evidence_summary"),
        },
        "tracks": {
            "01_act": {
                "actions": result.get("actions") or [],
                "blast_radius": radius,
                "tool_selection": result.get("tool_selection"),
            },
            "02_remember": {
                "session_id": result.get("session_id"),
                "memory": (result.get("path") or {}).get("memory"),
                "procedure": (result.get("path") or {}).get("procedure"),
            },
            "03_explain": {
                "sources": result.get("sources") or [],
                "handoffs": result.get("handoffs") or [],
                "owners": owners,
                "evidence_path_id": (result.get("path") or {}).get("evidence_path_id"),
                "checklist": result.get("checklist") or {},
            },
        },
        "graph_nodes": graph.get("nodes"),
        "graph_edges": graph.get("edges"),
        "node_vectors": vectors,
    }


def markdown_report(result: dict[str, Any], embedding: dict[str, Any] | None = None) -> str:
    system = result.get("system") or "unknown"
    lines = [
        f"# SALUS Investigation Report",
        "",
        f"**System:** {system}  ",
        f"**Domain:** {result.get('domain')}  ",
        f"**Confidence:** {round((result.get('confidence') or 0) * 100)}%  ",
        f"**Investigation:** {result.get('investigation_id')}  ",
        f"**Session:** {result.get('session_id')}  ",
        "",
        "## Brief",
        "An agent that acts on connected data, remembers what it learns, and shows how it got to each answer.",
        "",
        "## Track 01 — Act on connected data",
        f"- Actions: {', '.join(result.get('actions') or []) or 'none'}",
        f"- Blast radius: {json.dumps((embedding or {}).get('tracks', {}).get('01_act', {}).get('blast_radius', {}), default=str)}",
        "",
        "## Track 02 — Remember",
        f"- Session: {result.get('session_id')}",
        f"- Memory: {json.dumps((result.get('path') or {}).get('memory'), default=str)[:800]}",
        "",
        "## Track 03 — Explain / company brain",
        f"- Evidence: {result.get('evidence_summary')}",
        f"- Sources:",
    ]
    for s in result.get("sources") or []:
        lines.append(f"  - {s}")
    lines.extend(
        [
            "",
            "## Answer",
            "```",
            (result.get("answer") or "").replace("**", ""),
            "```",
            "",
            "## Handoffs",
        ]
    )
    for h in result.get("handoffs") or []:
        lines.append(f"- {h}")
    lines.extend(["", "## Checklist"])
    for k, v in (result.get("checklist") or {}).items():
        lines.append(f"- [{'x' if v else ' '}] {k}")
    lines.append("")
    return "\n".join(lines)


def html_report(result: dict[str, Any], embedding: dict[str, Any] | None = None) -> str:
    mdish = markdown_report(result, embedding)
    body = (
        mdish.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>\n")
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>SALUS Report</title>
<style>
body{{font-family:IBM Plex Sans,system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#13241c;background:#e7eee9}}
h1{{font-family:Bricolage Grotesque,sans-serif}}
code,pre{{font-family:IBM Plex Mono,monospace;white-space:pre-wrap}}
</style></head><body>{body}</body></html>"""
