# SALUS architecture

```mermaid
flowchart TB
  User[User / Alert] --> Router
  Router -->|Handoff| Inv[Investigator]
  Inv --> MCP[MCP graph tools]
  MCP --> Graph[(FalkorDB salus:tenant)]
  Inv -->|EvidencePath| Actor
  Actor -->|Handoff| Scribe
  Scribe --> Graph
  Actor --> Graph
```

## Domains

One schema. Systems carry `domain`:
`finance` | `healthcare` | `security` | `facilities` | `ops` | custom

## Stack

- FalkorDB Docker (`docker compose up -d`)
- Python `falkordb` client
- Multi-agent loop in `salus/agents.py`
- MCP server in `salus/mcp_server.py`
