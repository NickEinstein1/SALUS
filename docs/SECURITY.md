# SALUS security

## Controls

| Control | Behavior |
| --- | --- |
| API key | `X-API-Key` (or `api_key` query for SSE) required unless `SALUS_AUTH_DISABLED=true` |
| Admin seed | `POST /api/seed` requires `X-Admin-Key` (falls back to API key) |
| Tenant lock | Client `tenant_id` ignored unless in `SALUS_ALLOWED_TENANTS` |
| Input validation | IDs, people, tickets, severity, question length + Cypher keyword blocklist |
| Rate limits | Ask / mutate / general per-IP sliding windows |
| CORS | Allowlist only (`SALUS_CORS_ORIGINS`) |
| Security headers | CSP, X-Frame-Options DENY, nosniff, Referrer-Policy, COOP |
| Trusted hosts | Enforced when `SALUS_ENV=production` |
| OpenAPI | Disabled unless `SALUS_DEBUG=true` |
| Error leakage | Generic errors unless `SALUS_DEBUG=true` |
| Parameterized Cypher | Queries use params; identifiers validated before use |

## Production checklist

1. Set a long random `SALUS_API_KEY` (and optional `SALUS_ADMIN_KEY`)
2. Set `SALUS_ENV=production`
3. Set `FALKOR_PASSWORD` and do not expose FalkorDB ports publicly
4. Set `SALUS_CORS_ORIGINS` and `SALUS_ALLOWED_HOSTS` to your real domain
5. Put TLS in front (Caddy/nginx) and enable `SALUS_HSTS=true`
6. Never set `SALUS_AUTH_DISABLED=true` or `SALUS_DEBUG=true` in production
