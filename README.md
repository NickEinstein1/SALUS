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

## Quick start

```bash
# 1) FalkorDB
docker compose up -d

# 2) Python env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3) Load seed (tenant acme — multi-domain campus)
python -m salus.seed

# 4) Chat CLI
python -m salus.cli "Why are checkouts failing and who should own this?"

# 5) Verify every Track 01/02/03 judge bullet
python -m salus.cli verify

# 6) MCP server (Cursor / Claude)
python -m salus.mcp_server
```

Graph name: `salus:acme` · Browser: [http://localhost:3000](http://localhost:3000)  
Judge map: [`docs/JUDGE_CHECKLIST.md`](docs/JUDGE_CHECKLIST.md)

## Repo map

```
salus/           # Python package — agents, graph, MCP tools
schema/          # Canonical node & relationship schema
cypher/          # Indexes, seed, demo queries
docs/            # Track mapping + architecture
```
