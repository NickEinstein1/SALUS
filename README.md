# SALUS — Universal Company Nerve Agent

> One FalkorDB graph that **acts**, **remembers**, and **knows how any organization works** — finance, hospitals, security, facilities/HVAC, or anything else.

Built for [Graph Hacks: Context for AI Agents](https://www.wemakedevs.org/hackathons/falkordb?utm_source=luma) (WeMakeDevs × FalkorDB).  
Powered by [FalkorDB](https://docs.falkordb.com/getting-started).

## Demo video — watch and enjoy

[![SALUS demo](https://img.youtube.com/vi/786HaLG8UO0/maxresdefault.jpg)](https://youtu.be/786HaLG8UO0)

**→ [https://youtu.be/786HaLG8UO0](https://youtu.be/786HaLG8UO0)** (~2 min)

## Questions that work (try these)

Paste any of these into the path finder or the left SALUS chat (chat also recalls **graph memory** — episodes & facts):

**UI prompts**
- Why are checkouts failing and who should own this?
- Wing B lost cooling — what breaks and who do we page?
- Badge readers failing in wing B — who owns access control?

**Finance** — Why are checkouts failing? · Who owns payments-api? · What depends on ledger-db? · Is fraud involved in the checkout spike? · What is the blast radius of card-gateway?

**Healthcare** — Why is ehr-core slow? · What breaks if imaging-pacs goes down? · Who owns ehr-core and who knows EHR? · Trace the decision that EHR depends on Wing B cooling.

**Facilities** — Wing B lost cooling — what breaks? · Who do we page for hvac-wing-b? · How is ehr-core connected to building-mgmt?

**Security** — Who owns badge-controller? · Who knows access-control for wing B? · Who should unlock wing B after a badge outage?

**Memory / company brain** — What do we remember about payments-api? · Recall episodes about HVAC or Wing B · What runbooks exist for badge outages?

## What it does

Ask SALUS something like *“why are checkouts failing?”*, *“who owns the HVAC zone that lost cooling?”*, or *“who can unlock wing B after a badge outage?”*

It walks your org graph, recalls past incidents, decides what to do, and **shows the path** behind every answer.

| Track | How SALUS wins it |
| --- | --- |
| **01 — Act on connected data** | Multi-hop Cypher + graph tools via MCP → `Action` + `EvidencePath` |
| **02 — Memory & coordination** | Episodic / semantic / procedural memory, handoffs, shared state, **one graph per tenant** |
| **03 — Company brain** | People, teams, assets/systems, docs, tickets, decisions — industry-agnostic |

### Questions that work (after you know what SALUS does)

Use the same list above — start with the three UI chips, then branch by domain. Mention a system or keyword (`checkout`, `payments-api`, `ehr`, `hvac`, `wing b`, `badge`, `camera`) so the Router can map your ask. Follow-ups in the left chatbot pull **episodic + semantic memory** from FalkorDB before answering.

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
