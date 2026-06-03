# Next Steps

Status as of June 2026: the MVP is **built and running** end-to-end — RSS aggregation, per-story clustering, LLM-powered left/right comparisons (gpt-4o-mini), time-grouped archive, daily briefing, search, and newsletter capture. Backend on `:8000` (auto-refresh every 6h), frontend on `:8080`.

This document lists what to do next, in priority order. Each item notes rough effort (S/M/L) and why it matters.

---

## Phase 1 — Hardening & quick wins (do first)

These protect cost, reliability, and the core USP with little effort.

1. **Comparison caching** · S · *cost + speed*
   Today every scheduler cycle deletes and regenerates clusters in the 72h window, re-calling the LLM even for unchanged stories. Skip the LLM call when a cluster's set of article IDs is unchanged from an existing comparison. Cuts ongoing OpenAI cost to near-zero and speeds up each cycle.

2. **Improve both-sided coverage** · M · *the core USP*
   Many stories currently show "No right-leaning sources have covered this story yet." Add more right-leaning and centre-right world-news feeds (e.g. Washington Times, Fox World via a working feed, Spectator alternative, Times of London) and verify each returns items. The comparison only shines when both sides actually cover a story.

3. **Rotate & secure the API key** · S · *security*
   The current `OPENAI_API_KEY` was shared in chat. Regenerate it in the OpenAI dashboard, update `backend/.env`, and confirm `.env` stays gitignored (now handled).

4. **Graceful API error states on the frontend** · S · *polish*
   The homepage/story pages already show error boxes, but add a small "last successful update" indicator and retry button so transient backend hiccups are obvious to users.

---

## Phase 2 — Analysis quality & product features

5. **Embedding-based clustering** · L · *quality*
   Replace (or augment) the TF-IDF + entity heuristic in `pipeline/clustering.py` with sentence embeddings (OpenAI `text-embedding-3-small` or a local `sentence-transformers` model) and cosine thresholds. Tighter, more accurate story grouping — especially for stories that use different vocabulary for the same event.

6. **Send the daily briefing email** · M · *closes the loop*
   Subscribers are captured in the `subscribers` table but nothing is sent. Wire up an email provider (Resend, Postmark, or SES), render the `/api/briefing/daily` payload into an HTML email, and schedule a once-daily send. Add an unsubscribe link + endpoint.

7. **Prompt & schema tuning for comparisons** · S/M · *quality*
   Iterate on the LLM prompt in `pipeline/analysis.py`: ask for tighter, evidence-anchored bullets; cap lengths; optionally include a "confidence" or "neutrality" note. Consider a centre/establishment framing column to complement left/right.

8. **Story permalinks that survive re-clustering** · M · *UX*
   Cluster IDs can change when the 72h window rebuilds, so bookmarked links may break. Add a stable slug/hash per story (based on title + earliest article) and resolve by slug.

9. **"Read it yourself" enhancements** · S · *trust*
   On the story page, group the source list by Left / Centre / Right with counts, and show each source's bias rating. Reinforces the transparency angle.

---

## Phase 3 — Scale & deployment

10. **Deploy to the web** · L · *go live*
    - Backend: containerise the FastAPI app, move SQLite → **PostgreSQL** (schema already compatible), run on Render/Railway/Fly.io with the scheduler as a worker or cron.
    - Frontend: host the static site on Netlify/Vercel/Cloudflare Pages and point `API_BASE` in `js/app.js` at the deployed API (env-driven).
    - Add a real domain + HTTPS and lock CORS to that origin.

11. **Full-article scraping** · M · *richer analysis*
    Currently only RSS summaries are analysed. Fetch and clean full article text (respecting robots.txt / paywalls) so comparisons are based on complete coverage, not blurbs.

12. **Monitoring & analytics** · M · *operations*
    Add structured logging, a health/metrics endpoint, OpenAI spend tracking, and basic privacy-friendly analytics (Plausible/Umami) to see which stories get read.

13. **Accounts & personalisation** · L · *retention*
    Optional user accounts to follow topics, save stories, and choose briefing frequency.

---

## Suggested order

Start with **#1 (caching)**, **#2 (more right-leaning feeds)**, and **#3 (rotate key)** — they're cheap and directly improve cost, the USP, and security. Then **#6 (email)** to make the newsletter real, and **#5 (embeddings)** once you want a noticeable quality jump. Tackle Phase 3 when you're ready to put it in front of real users.
