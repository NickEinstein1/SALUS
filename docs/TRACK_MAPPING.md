# How SALUS hits all three tracks

Product: **SALUS** — universal org nerve agent (any industry via `domain`).

Verify anytime: `python -m salus.cli verify` → all judge bullets must pass.

## Track 01 — Act on connected data

| Criterion | Implementation |
| --- | --- |
| Multi-hop reasoning | `blast_radius` on `DEPENDS_ON*` |
| Graph queries & algorithms as tools | PageRank, betweenness, WCC, shortestPath, BFS, SPpaths in `algorithms.py` + MCP |
| Tool selection through MCP | `tool_router.select_tools` over the MCP catalog (LLM if `OPENAI_API_KEY`) |
| Actions from graph | `page_owner`, `assign_ticket`, `open_ticket_from_finding` |
| Explainable results | `EvidencePath` + ordered `ToolCall` chain |

## Track 02 — Memory & coordination

| Criterion | Implementation |
| --- | --- |
| Episodic / semantic / procedural | `Episode`, `Fact`, `Procedure` load + write each run |
| Persistent conversation history | `Session` / `Message` with `seq`; `CONTINUES` across sessions |
| Shared state & handoffs | `SharedState` + `Handoff` between Router/Investigator/Actor/Scribe |
| High-concurrency R/W | Optimistic CAS on `SharedState.version` (thread-verified) |
| Per-user / per-tenant memory | graph `salus:{tenant}` + `Session.user_id` isolation |

## Track 03 — Company brain

| Criterion | Implementation |
| --- | --- |
| Docs / tickets / chats in one graph | `ingest.py` + `collect_sources` |
| Who owns / who knows | `OWNS`, `KNOWS`, `WORKS_ON` |
| Trace decisions to source | `trace_decisions` + `SUPERSEDES` / authors |
| Keep knowledge current | `invalidate_fact` → `INVALIDATES` + `valid_to` |
| Answers with clear sources | runbook URLs, decisions, ticket keys on every answer |
