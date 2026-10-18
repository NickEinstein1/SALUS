# Deploy SALUS on Vercel

## Fix “api offline” (most common)

Your deployment URL is behind **Vercel Authentication** (SSO). Browsers get a login wall; `/api/health` redirects to `vercel.com/sso-api` and the UI shows **api offline**.

URLs that look like `salus-eiv1cec6f-….vercel.app` are often **Preview** deployments — protection is usually **on** for those by default.

**Disable it (required):**

1. Open [Vercel Dashboard](https://vercel.com/dashboard) → your **SALUS** project  
2. **Settings** → **Deployment Protection**  
3. Set **Vercel Authentication** to **Only Preview Deployments** *or* **Disabled**  
   - If you keep protection on Previews, open the **Production** domain instead of the preview hash URL  
4. Save  
5. **Deployments** → open the deployment marked **Production** → **Visit**  
6. In an **Incognito** window, open `https://YOUR-PRODUCTION-URL/api/health`  

**Pass check:** you see raw JSON (`"ok": true` or `"ok": false`) — **not** a Vercel login page and **not** the text `Protected by Vercel Authentication`.

If Incognito still redirects to login, protection is still on — the app code cannot override that.

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

## “api offline” while `/api/health` is OK

Production `SALUS_API_KEY` is **not** `salus-dev-change-me`. Paste the real key from Vercel → Settings → Environment Variables into the UI top bar, blur/change to save, then refresh. The graph endpoint requires that key; a 401 used to flip the status pill to “api offline”.

**Production URL:** https://salus-six.vercel.app  
