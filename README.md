# SALUS — Universal Company Nerve Agent

> One FalkorDB graph that **acts**, **remembers**, and **knows how any organization works** — finance, hospitals, security, facilities/HVAC, or anything else.

Built for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb?utm_source=luma) (WeMakeDevs × FalkorDB).  
Powered by [FalkorDB](https://docs.falkordb.com/getting-started).

## What it does

Ask SALUS something like *“why are checkouts failing?”*, *“who owns the HVAC zone that lost cooling?”*, or *“who can unlock wing B after a badge outage?”*

It walks your org graph, recalls past incidents, decides what to do, and **shows the path** behind every answer.

| Track | How SALUS wins it |
| --- | --- |
| **01 — Act on connected data** | Multi-hop Cypher + graph tools via MCP → `Action` + `EvidencePath` |
| **02 — Memory & coordination** | Episodic / semantic / procedural memory, handoffs, shared state, **one graph per tenant** |
| **03 — Company brain** | People, teams, assets/systems, docs, tickets, decisions — industry-agnostic |

## Universal by design

Labels are industry-neutral (`Person`, `System`, `Ticket`, …).  
Each `System` / `Project` / `Skill` carries a `domain` (e.g. `finance`, `healthcare`, `security`, `facilities`).  
Same agent loop works for a bank, a hospital, a campus, or a factory.

## Quick start — hosted UI

```bash
# Full stack (FalkorDB + SALUS web UI)
docker compose up -d --build

# Open the agent console
open http://localhost:8080
```

Or locally:

```bash
docker compose up -d falkordb
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m salus.seed
python -m salus.api
# → http://localhost:8080
```

The UI shows the **agent sequence** (Router → Investigator → Actor → Scribe), a live **company graph**, and the **explainable answer path** as SALUS runs.

### CLI / MCP / verify

```bash
python -m salus.cli "Why are checkouts failing and who should own this?"
python -m salus.cli verify
python -m salus.mcp_server
```

Graph name: `salus:acme` · FalkorDB Browser: [http://localhost:3000](http://localhost:3000) · SALUS UI: [http://localhost:8080](http://localhost:8080)  
Judge map: [`docs/JUDGE_CHECKLIST.md`](docs/JUDGE_CHECKLIST.md) · Security: [`docs/SECURITY.md`](docs/SECURITY.md)

Default API key (dev): `salus-dev-change-me` — paste into the UI top bar / set `SALUS_API_KEY`.

## Repo map

```
salus/           # Python package — agents, graph, MCP tools
schema/          # Canonical node & relationship schema
cypher/          # Indexes, seed, demo queries
docs/            # Track mapping + architecture
```
