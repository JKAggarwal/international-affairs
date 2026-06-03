# Deployment Guide

Goal: put the live site at **https://internationalaffairs.org.uk** with the API at **https://api.internationalaffairs.org.uk**.

## Architecture (free tier)

| Piece | Host | Cost | Notes |
|-------|------|------|-------|
| Frontend (`website/`) | **Netlify** | Free | Static files, custom domain, auto HTTPS |
| Backend API (`backend/`) | **Render** (Web Service, free) | Free | Sleeps when idle; woken by cron |
| Database | **Neon** (Postgres, free) | Free | Durable, survives restarts |
| 6-hourly news fetch | **cron-job.org** | Free | Calls `/api/fetch-news` (the in-app scheduler is off on free tier) |
| Domain / DNS | **Squarespace** (you already own it) | — | Just edit DNS records |

> Trade-off you accepted: on the free tier the API **sleeps after ~15 min idle**, so the first visit after a quiet period takes ~30–50s to wake. Upgrading the Render service to the paid instance (~$7/mo) removes this and lets you use the built-in scheduler instead of the external cron.

The code is already prepared for this: database, CORS, scheduler, fetch trigger and the frontend API URL are all environment-driven (see `backend/.env.example`).

---

## Step 0 — Accounts you'll need (all free)

- [GitHub](https://github.com) (to hold the code; Render + Netlify deploy from it)
- [Neon](https://neon.tech)
- [Render](https://render.com)
- [Netlify](https://netlify.com)
- [cron-job.org](https://cron-job.org)

---

## Step 1 — Push the project to GitHub

From the project root:

```bash
cd "/Users/jaiaggarwal/Desktop/international affairs"
git init
git add .
git commit -m "International Affairs MVP"
```

`.gitignore` already excludes `.env`, the SQLite `.db`, and caches, so **your OpenAI key is not committed.** Verify:

```bash
git status --ignored   # .env and *.db should appear under "Ignored files"
```

Create an empty repo on GitHub (no README), then:

```bash
git remote add origin https://github.com/<your-username>/international-affairs.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Create the Postgres database (Neon)

1. Neon → **New Project** → name it `international-affairs`.
2. Copy the **connection string** (looks like `postgresql://user:pass@ep-xxx.eu-west-2.aws.neon.tech/neondb?sslmode=require`).
3. Keep it handy — it becomes `DATABASE_URL` in Step 3.

Tables are created automatically on first boot; no manual schema setup.

---

## Step 3 — Deploy the backend (Render)

1. Render → **New → Web Service** → connect your GitHub repo.
2. Configure:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
3. Add **Environment Variables** (Settings → Environment):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | *(the Neon string from Step 2)* |
   | `OPENAI_API_KEY` | *(your key — rotate it first, it was shared in chat)* |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `ALLOWED_ORIGINS` | `https://internationalaffairs.org.uk,https://www.internationalaffairs.org.uk` |
   | `ENABLE_SCHEDULER` | `false` |
   | `FETCH_ON_STARTUP` | `auto` |
   | `FETCH_TOKEN` | *(a long random string — see below)* |
   | `PYTHONUNBUFFERED` | `1` *(so pipeline logs appear in Render immediately)* |

   Generate a token locally:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. Deploy. On the **first** boot the database is empty, so it auto-fetches and builds the first batch of stories (takes a minute or two — watch the logs).
5. Once live, note your Render URL, e.g. `https://international-affairs-api.onrender.com`. Test it:
   ```bash
   curl https://international-affairs-api.onrender.com/api/stories?limit=1
   ```

### Custom subdomain for the API
In Render → your service → **Settings → Custom Domains**, add `api.internationalaffairs.org.uk`. Render shows a **CNAME target** (e.g. `international-affairs-api.onrender.com`) — you'll use it in Step 5.

---

## Step 4 — Deploy the frontend (Netlify)

1. Netlify → **Add new site → Import from Git** → pick your repo.
2. Build settings (or leave defaults — `netlify.toml` in the repo sets this):
   - **Base directory:** *(leave empty)*
   - **Build command:** *(leave empty — it's static)*
   - **Publish directory:** `website`
3. Deploy. You'll get a URL like `https://your-site-name.netlify.app`. Stories should load there immediately (preview uses the Render API URL until `api.` DNS is live).
4. The frontend already targets `https://api.internationalaffairs.org.uk/api` automatically when not on localhost (see `website/js/app.js`), so no code change is needed once DNS is set.

### Custom domain for the site
Netlify → **Domain settings → Add custom domain** → `internationalaffairs.org.uk` (add `www` too). Netlify will show the DNS targets for Step 5.

---

## Step 5 — Point Squarespace DNS

In Squarespace: **Settings → Domains → internationalaffairs.org.uk → DNS / DNS Settings**, add these records (use the exact targets Netlify/Render showed you):

| Type | Host / Name | Value | For |
|------|-------------|-------|-----|
| A | `@` (root) | `75.2.60.5` | Netlify apex (confirm IP in Netlify's panel) |
| CNAME | `www` | `your-site-name.netlify.app` | Netlify www |
| CNAME | `api` | `international-affairs-api.onrender.com` | Render API |

Notes:
- Use the values **your** Netlify/Render dashboards display — the ones above are examples.
- DNS can take 5 minutes to a few hours to propagate.
- HTTPS certificates are issued automatically by Netlify and Render once DNS resolves (you may need to click "Provision certificate").
- If Squarespace won't let you set an `A` record on the root, the alternative is to switch the domain's nameservers to Netlify DNS (Netlify → Domains → "Use Netlify DNS") and manage all records there instead.

---

## Step 6 — Schedule the 6-hourly fetch (cron-job.org)

Since `ENABLE_SCHEDULER=false` on the free tier, an external cron keeps the news fresh:

1. cron-job.org → **Create cronjob**.
2. **URL:** `https://api.internationalaffairs.org.uk/api/fetch-news`
3. **Request method:** `POST`
4. **Headers:** add `X-Fetch-Token: <your FETCH_TOKEN from Step 3>`
5. **Schedule:** every 6 hours.
6. Save and run it once manually to confirm you get `{"message":"News fetch started in background"}`.

(Without the correct token you'll get `401` — that's the protection working.)

---

## Step 7 — Verify everything

- Visit `https://internationalaffairs.org.uk` — stories, briefing, search should load.
- `https://api.internationalaffairs.org.uk/` returns the API info JSON.
- Subscribe with a test email; confirm a second attempt says "already subscribed".
- Trigger the cron once; refresh the site to see updated stories.

---

## Maintenance & gotchas

- **Cold starts:** first visit after idle is slow on the free tier. Upgrade Render to a paid instance to fix, and then you can set `ENABLE_SCHEDULER=true` and delete the cron job.
- **Updating the site:** `git push` to `main` — Render and Netlify redeploy automatically.
- **Costs:** Render free + Neon free + Netlify free = £0. OpenAI is the only spend (~£/$ a couple per month at 6-hourly with `gpt-4o-mini`). Set a monthly usage limit in the OpenAI dashboard.
- **Secrets:** never commit `.env`. All secrets live in the Render dashboard.
- **Email delivery** (sending the daily briefing to subscribers) is still a future step — see `NEXT-STEPS.md`.
