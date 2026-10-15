"""SALUS MCP server — full Track 01/02/03 tool surface."""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from salus import actions, algorithms, ingest, knowledge, memory, tools
from salus.agents import run_salus
from salus.config import settings

server = MCPServer(
    name="salus",
    version="0.2.0",
    instructions=(
        "SALUS universal org nerve agent on FalkorDB. "
        "Select tools for multi-hop reasoning, graph algorithms, memory, "
        "company-brain queries, ingest, and actions. Prefer salus_investigate "
        "for the full multi-agent loop with EvidencePath."
    ),
)


def _j(data) -> str:
    return json.dumps(data, indent=2, default=str)


@server.tool()
def salus_list_systems(domain: str | None = None) -> str:
    """List systems. Optional domain: finance, healthcare, security, facilities, ops."""
    return _j(tools.list_systems(domain=domain))


@server.tool()
def salus_blast_radius(system_name: str, max_hops: int = 3) -> str:
    """Multi-hop DEPENDS_ON blast radius."""
    return _j(tools.blast_radius(system_name, max_hops=max_hops))


@server.tool()
def salus_who_owns_and_knows(system_name: str) -> str:
    """Who owns a system and who has domain skills."""
    return _j(tools.who_owns_and_knows(system_name))


@server.tool()
def salus_recall_memory(about: str, limit: int = 5) -> str:
    """Episodic episodes + semantic facts about an entity."""
    return _j(tools.recall_memory(about, limit=limit))


@server.tool()
def salus_find_runbooks(system_name: str) -> str:
    """Documents/runbooks referencing a system."""
    return _j(tools.find_runbooks(system_name))


@server.tool()
def salus_trace_decisions(system_name: str) -> str:
    """Trace decisions to authors, projects, and SUPERSEDES chain."""
    return _j(knowledge.trace_decisions(system_name))


@server.tool()
def salus_collect_sources(system_name: str) -> str:
    """Collect docs, tickets, and chat mentions as answer sources."""
    return _j(knowledge.collect_sources(system_name))


@server.tool()
def salus_pagerank(limit: int = 10) -> str:
    """PageRank over System DEPENDS_ON — graph algorithm tool."""
    return _j(algorithms.pagerank_systems(limit=limit))


@server.tool()
def salus_betweenness(limit: int = 10) -> str:
    """Betweenness centrality over System DEPENDS_ON."""
    return _j(algorithms.betweenness_systems(limit=limit))


@server.tool()
def salus_connected_components() -> str:
    """Weakly connected components (WCC) over systems."""
    return _j(algorithms.connected_components())


@server.tool()
def salus_shortest_path(source: str, target: str) -> str:
    """Shortest DEPENDS_ON path between two systems."""
    return _j(algorithms.shortest_dependency_path(source, target))


@server.tool()
def salus_bfs(system_name: str, max_depth: int = 3) -> str:
    """BFS reachability from a system via DEPENDS_ON."""
    return _j(algorithms.bfs_from_system(system_name, max_depth=max_depth))


@server.tool()
def salus_load_procedure(name: str | None = None) -> str:
    """Load procedural memory (how-to steps) for agents."""
    return _j(memory.load_procedure(name) or {})


@server.tool()
def salus_shared_state(key: str = "active_incident") -> str:
    """Read multi-agent shared state blackboard."""
    return _j(memory.read_shared_state(key=key))


@server.tool()
def salus_update_shared_state(key: str, patch_json: str, expected_version: int) -> str:
    """CAS update shared state (high-concurrency safe). patch_json merges into current value."""
    cur = memory.read_shared_state(key=key)
    base = dict(cur.get("value") or {})
    base.update(json.loads(patch_json))
    return _j(memory.cas_shared_state(key, expected_version, base))


@server.tool()
def salus_session_history(session_id: str) -> str:
    """Persistent conversation history for a session."""
    return _j(memory.session_history(session_id))


@server.tool()
def salus_user_memory(user_id: str) -> str:
    """Per-user cross-session memory (tenant graph isolation + user_id)."""
    return _j(memory.cross_session_memory(user_id))


@server.tool()
def salus_ingest_document(
    title: str,
    summary: str,
    domain: str = "ops",
    url: str = "",
    systems_csv: str = "",
) -> str:
    """Ingest a document into the company graph."""
    systems = [s.strip() for s in systems_csv.split(",") if s.strip()]
    return _j(
        ingest.ingest_document(
            title=title, summary=summary, domain=domain, url=url or None, references_systems=systems
        )
    )


@server.tool()
def salus_ingest_ticket(
    key: str,
    title: str,
    severity: str = "SEV-3",
    domain: str = "ops",
    systems_csv: str = "",
) -> str:
    """Ingest a ticket into the company graph."""
    systems = [s.strip() for s in systems_csv.split(",") if s.strip()]
    return _j(
        ingest.ingest_ticket(
            key=key, title=title, severity=severity, domain=domain, about_systems=systems
        )
    )


@server.tool()
def salus_ingest_chat(content: str, user_id: str, systems_csv: str = "") -> str:
    """Ingest a chat message (links into Session + optional System MENTIONS)."""
    systems = [s.strip() for s in systems_csv.split(",") if s.strip()]
    return _j(ingest.ingest_chat(content=content, user_id=user_id, mention_systems=systems))


@server.tool()
def salus_invalidate_fact(fact_id: str, reason: str, replacement: str = "") -> str:
    """Keep knowledge current: invalidate a Fact and optionally replace it."""
    return _j(
        knowledge.invalidate_fact(
            fact_id, reason=reason, replacement_statement=replacement or None
        )
    )


@server.tool()
def salus_page_owner(person_name: str, system_name: str = "", ticket_key: str = "") -> str:
    """Action: page an owner (graph mutation)."""
    return _j(
        actions.page_owner(
            person_name,
            system_name=system_name or None,
            ticket_key=ticket_key or None,
        )
    )


@server.tool()
def salus_investigate(question: str, user_id: str = "person:sam") -> str:
    """Full SALUS loop: Router→Investigator→Actor→Scribe with EvidencePath + checklist."""
    result = run_salus(question, user_id=user_id)
    return _j(
        {
            "answer": result.answer,
            "domain": result.domain,
            "system": result.system,
            "owners": result.owners,
            "confidence": result.confidence,
            "actions": result.actions,
            "sources": result.sources,
            "evidence_summary": result.evidence_summary,
            "handoffs": result.handoffs,
            "investigation_id": result.investigation_id,
            "session_id": result.session_id,
            "user_id": result.user_id,
            "tool_selection": result.tool_selection,
            "checklist": result.checklist,
            "path": result.path,
            "graph": settings.graph_name,
        }
    )


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
