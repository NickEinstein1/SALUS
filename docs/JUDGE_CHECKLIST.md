# SALUS — Judge scoring checklist (Tracks 01 / 02 / 03)

Run: `python -m salus.cli verify`

| Track | Bullet | Implementation |
| --- | --- | --- |
| **01** | Multi-hop reasoning | `tools.blast_radius` / `DEPENDS_ON*` |
| **01** | Graph queries & algorithms as tools | `algorithms.py`: PageRank, betweenness, WCC, shortestPath, BFS, SPpaths |
| **01** | Tool selection through MCP | `tool_router.select_tools` over MCP catalog (+ optional `OPENAI_API_KEY`) |
| **01** | Actions based on what the graph shows | `actions.page_owner` / `assign_ticket` / `open_ticket_from_finding` |
| **01** | Explainable results | `EvidencePath` + `ToolCall` chain on every investigation |
| **02** | Episodic / semantic / procedural | `Episode`, `Fact`, `Procedure` loaded & written each run |
| **02** | Persistent conversation history | `Session` + `Message` with `seq` |
| **02** | Shared state & handoffs | `SharedState` CAS + `Handoff` edges between agents |
| **02** | High-concurrency R/W | `cas_shared_state` / `update_shared_state_with_retry` (verified under threads) |
| **02** | Separate memory per user/tenant | graph `salus:{tenant}` + `Session.user_id` isolation |
| **03** | Docs, tickets, chats in one graph | `ingest.py` + `collect_sources` |
| **03** | Who owns / who knows | `OWNS` + `KNOWS` via `who_owns_and_knows` |
| **03** | Trace decisions to source | `knowledge.trace_decisions` + `SUPERSEDES` |
| **03** | Keep knowledge current | `invalidate_fact` / `SUPERSEDES` / `valid_to` |
| **03** | Answers with clear sources | runbook URLs, decision titles, ticket keys on every answer |
