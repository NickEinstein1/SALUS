# Deploy SALUS on Vercel

## Fix “api offline” (most common)

Your deployment URL is behind **Vercel Authentication** (SSO). Browsers get a login wall; `/api/health` redirects to `vercel.com/sso-api` and the UI shows **api offline**.

**Disable it:**

1. Open [Vercel Dashboard](https://vercel.com/dashboard) → your **SALUS** project  
2. **Settings** → **Deployment Protection**  
3. Set **Vercel Authentication** to **Disabled** (or only protect Preview, not Production)  
4. Save → redeploy or hard-refresh the site  

You want a public URL like `https://salus-….vercel.app` that returns JSON from `/api/health` without signing into Vercel.

## Required environment variables

| Name | Example |
|------|---------|
| `FALKOR_HOST` | Cloud hostname |
| `FALKOR_PORT` | `52731` |
| `FALKOR_USERNAME` | `falkordb` |
| `FALKOR_PASSWORD` | instance password |
| `FALKOR_SSL` | `false` on Free tier |
| `SALUS_API_KEY` | strong key (paste in UI) |
| `SALUS_CORS_ORIGINS` | `https://your-app.vercel.app` (optional; auto-detected) |

## After deploy

1. Open `/api/health` — should be `{"ok":true,"nodes":63,…}`  
2. If `ok:false` / graph unavailable, fix `FALKOR_*` and redeploy  
3. Seed once if empty: `POST /api/seed` with `X-Admin-Key` / admin key, or run seed locally against Cloud  
