# SALUS Graph Schema (FalkorDB / OpenCypher)

**Graph naming (multi-tenant):** `salus:{tenant_id}`  
Example: `salus:acme`

Industry-agnostic property graph. Domains are **data**, not separate schemas.

```
LAYER C — ACTION & EXPLANATION (Track 01)
  Finding · Investigation · Action · EvidencePath · ToolCall
LAYER B — MEMORY & COORDINATION (Track 02)
  Agent · Session · Message · Episode · Fact · Procedure · Handoff · SharedState
LAYER A — ORG BRAIN (Track 03) — any industry
  Person · Team · Project · System · Document · Ticket · Decision · Skill · Channel · Tenant
```

`System.domain` / `Project.domain` / `Skill.domain` examples:
`finance` · `healthcare` · `security` · `facilities` · `identity` · `ops` · `custom:*`

---

## Layer A — Org brain (Track 03)

| Label | Key properties | Purpose |
| --- | --- | --- |
| `Tenant` | `id`, `name`, `industries[]`, `created_at` | Org root |
| `Person` | `id`, `name`, `email`, `role`, `timezone`, `status` | Anyone accountable |
| `Team` | `id`, `name`, `mission`, `domain` | Org unit |
| `Project` | `id`, `name`, `status`, `priority`, `domain`, `started_at` | Initiative |
| `System` | `id`, `name`, `kind`, `env`, `criticality`, `domain` | Service, device, EHR, HVAC, badge, API, … |
| `Document` | `id`, `title`, `source`, `url`, `domain`, `updated_at`, `summary` | Runbooks, policies, SOPs |
| `Ticket` | `id`, `key`, `title`, `status`, `severity`, `domain`, `created_at` | Incident / request |
| `Decision` | `id`, `title`, `status`, `domain`, `decided_at`, `rationale` | ADR / clinical / security policy |
| `Skill` | `id`, `name`, `domain` | Expertise |
| `Channel` | `id`, `name`, `platform` | Slack / radio / email |

### Relationships

`MEMBER_OF` · `REPORTS_TO` · `OWNS` · `WORKS_ON` · `USES` · `DEPENDS_ON` · `KNOWS` · `AUTHORED` · `REFERENCES` · `ABOUT` · `ASSIGNED_TO` · `DECIDED_FOR` · `SUPERSEDES` · `POSTED_IN` · `MENTIONS`

---

## Layer B — Memory (Track 02)

| Label | Memory type |
| --- | --- |
| `Episode` | Episodic — what happened |
| `Fact` | Semantic — believed truth (`valid_from` / `valid_to`) |
| `Procedure` | Procedural — how to respond |
| `Agent` `Session` `Message` `Handoff` `SharedState` | Coordination |

---

## Layer C — Action (Track 01)

| Label | Purpose |
| --- | --- |
| `Finding` | Alert / anomaly from any domain |
| `Investigation` | Multi-hop reasoning run |
| `ToolCall` | MCP / Cypher / algorithm call |
| `EvidencePath` | Explainable path behind the answer |
| `Action` | Assign, page, escalate, open ticket, update fact |

Rule: every Investigation produces ≥1 `EvidencePath` before an `Action`.
