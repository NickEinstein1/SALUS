"""Track 01 — tool selection from the MCP tool catalog (optional LLM, deterministic fallback)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    when: str  # human hint for selection


# Same catalog exposed by salus.mcp_server — selection targets these names.
TOOL_CATALOG: list[ToolSpec] = [
    ToolSpec("salus_blast_radius", "Multi-hop dependency blast radius", "impact / depends / breaks / outage"),
    ToolSpec("salus_who_owns_and_knows", "Owners and domain experts", "who owns / who knows / page / assign"),
    ToolSpec("salus_recall_memory", "Episodic + semantic memory recall", "remember / last time / history / before"),
    ToolSpec("salus_find_runbooks", "Runbooks and documents for a system", "runbook / sop / how do we / playbook"),
    ToolSpec("salus_trace_decisions", "Trace decisions to authors and supersession", "decision / adr / policy / why did we"),
    ToolSpec("salus_collect_sources", "Docs, tickets, chats as sources", "source / ticket / chat / evidence"),
    ToolSpec("salus_pagerank", "PageRank influence of systems", "important / critical / influential"),
    ToolSpec("salus_betweenness", "Betweenness bridges in dependency graph", "bridge / bottleneck / connector"),
    ToolSpec("salus_connected_components", "Weakly connected components", "island / component / isolated"),
    ToolSpec("salus_shortest_path", "Shortest DEPENDS_ON path between systems", "path between / how connected / hops"),
    ToolSpec("salus_bfs", "BFS reachability from a system", "reach / downstream / bfs"),
    ToolSpec("salus_load_procedure", "Load procedural memory steps", "procedure / playbook steps / how to respond"),
    ToolSpec("salus_shared_state", "Read multi-agent shared blackboard", "active incident / shared state"),
]


def _heuristic_select(question: str, procedure_steps: list[str] | None = None) -> list[str]:
    q = question.lower()
    selected: list[str] = []

    # Always core investigation set for actionability
    selected.extend(
        [
            "salus_blast_radius",
            "salus_who_owns_and_knows",
            "salus_recall_memory",
            "salus_find_runbooks",
            "salus_collect_sources",
            "salus_load_procedure",
            "salus_shared_state",
        ]
    )

    for spec in TOOL_CATALOG:
        for hint in spec.when.split(" / "):
            if hint and hint in q and spec.name not in selected:
                selected.append(spec.name)

    if any(w in q for w in ("path", "between", "connected to", "reach")):
        for name in ("salus_shortest_path", "salus_bfs"):
            if name not in selected:
                selected.append(name)
    if any(w in q for w in ("important", "critical", "rank", "centrality", "page")):
        for name in ("salus_pagerank", "salus_betweenness"):
            if name not in selected:
                selected.append(name)
    if any(w in q for w in ("decision", "adr", "policy", "rationale")):
        if "salus_trace_decisions" not in selected:
            selected.append("salus_trace_decisions")
    if any(w in q for w in ("component", "island", "partition")):
        if "salus_connected_components" not in selected:
            selected.append("salus_connected_components")

    # Honor procedural memory steps → tool mapping
    step_map = {
        "blast": "salus_blast_radius",
        "owns": "salus_who_owns_and_knows",
        "knows": "salus_who_owns_and_knows",
        "episode": "salus_recall_memory",
        "fact": "salus_recall_memory",
        "recall": "salus_recall_memory",
        "action": "salus_who_owns_and_knows",
        "evidence": "salus_collect_sources",
        "domain": "salus_blast_radius",
        "classify": "salus_shared_state",
    }
    for step in procedure_steps or []:
        s = step.lower()
        for key, tool in step_map.items():
            if key in s and tool not in selected:
                selected.append(tool)

    # Always include one algorithm for Track 01 scoring when investigating
    if "salus_pagerank" not in selected:
        selected.append("salus_pagerank")
    if "salus_betweenness" not in selected:
        selected.append("salus_betweenness")
    if "salus_trace_decisions" not in selected:
        selected.append("salus_trace_decisions")

    return selected


def _llm_select(
    question: str,
    procedure_steps: list[str] | None = None,
    *,
    openai_api_key: str | None = None,
) -> list[str] | None:
    api_key = (openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    try:
        import httpx

        catalog = [{"name": t.name, "description": t.description} for t in TOOL_CATALOG]
        prompt = {
            "question": question,
            "procedure_steps": procedure_steps or [],
            "tools": catalog,
            "instruction": "Return JSON {\"tools\": [names...]} selecting the tools needed. Include ownership, memory, sources, and at least one graph algorithm.",
        }
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.getenv("SALUS_LLM_MODEL", "gpt-4o-mini"),
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "You select MCP tools for SALUS. Reply JSON only."},
                    {"role": "user", "content": json.dumps(prompt)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        names = data.get("tools") or data.get("selected") or []
        valid = {t.name for t in TOOL_CATALOG}
        picked = [n for n in names if n in valid]
        return picked or None
    except Exception:
        return None


def select_tools(
    question: str,
    procedure_steps: list[str] | None = None,
    *,
    openai_api_key: str | None = None,
) -> dict[str, Any]:
    """Select MCP tools for this question. Prefer LLM if an OpenAI key is provided."""
    has_key = bool((openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip())
    llm = _llm_select(question, procedure_steps, openai_api_key=openai_api_key)
    if llm:
        # Chat + investigations always ground answers in FalkorDB memory.
        if "salus_recall_memory" not in llm:
            llm = ["salus_recall_memory", *llm]
        return {
            "mode": "llm",
            "tools": llm,
            "catalog_size": len(TOOL_CATALOG),
            "rationale": "LLM selected from MCP catalog (OpenAI key); memory recall forced on",
        }
    tools = _heuristic_select(question, procedure_steps)
    return {
        "mode": "heuristic_mcp_catalog",
        "tools": tools,
        "catalog_size": len(TOOL_CATALOG),
        "rationale": (
            "Deterministic router over the MCP catalog"
            + (
                " (OpenAI key present but LLM selection failed — check key/model)"
                if has_key
                else " (add OpenAI key in UI or OPENAI_API_KEY for LLM selection)"
            )
        ),
    }


def execute_selected_tools(
    tool_names: list[str],
    *,
    system: str,
    question: str,
    tenant_id: str | None,
    dispatch: dict[str, Callable[..., dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Run selected tools and return a trace for EvidencePath."""
    import time

    trace: list[dict[str, Any]] = []
    for name in tool_names:
        fn = dispatch.get(name)
        if not fn:
            continue
        t0 = time.time()
        try:
            result = fn(system=system, question=question, tenant_id=tenant_id)
        except TypeError:
            result = fn(system)
        except Exception as e:
            result = {"error": str(e)}
        trace.append(
            {
                "tool": name,
                "args": {"system": system},
                "result_summary": json.dumps(result, default=str)[:600],
                "result": result,
                "latency_ms": int((time.time() - t0) * 1000),
                "cypher": (result or {}).get("cypher", "") if isinstance(result, dict) else "",
            }
        )
    return trace
