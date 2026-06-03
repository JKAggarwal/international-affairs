from dotenv import load_dotenv
load_dotenv()  # read backend/.env (e.g. OPENAI_API_KEY) before anything else

import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from database import get_db, init_db
from schemas import (
    StoryListItem, StoryDetail, SourceResponse, NewsletterSignup,
    SubscribeResponse, SearchResult, DailyBriefing,
)
import crud

# --- Configuration (env-driven so local and production differ only by env) ---
def _origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    # Sensible local defaults for development.
    return [
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]

ALLOWED_ORIGINS = _origins()
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
FETCH_TOKEN = os.getenv("FETCH_TOKEN", "")  # if set, /api/fetch-news requires it
# "auto" = fetch on startup only when the database is empty; or "true"/"false".
FETCH_ON_STARTUP = os.getenv("FETCH_ON_STARTUP", "auto").lower()

scheduler = BackgroundScheduler()

def _run_pipeline_task(full_recluster: bool = False):
    """Run fetch pipeline with flushed logs (Render buffers stdout otherwise)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] News pipeline started (full_recluster={full_recluster})", flush=True)
    try:
        from pipeline.fetcher import run_pipeline
        run_pipeline(full_recluster=full_recluster)
        done = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{done}] News pipeline finished OK", flush=True)
    except Exception as e:  # noqa: BLE001
        failed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{failed}] News pipeline FAILED: {e}", flush=True)
        raise


def scheduled_fetch(full_recluster: bool = False):
    """Run the news fetch pipeline on schedule."""
    _run_pipeline_task(full_recluster=full_recluster)


def _needs_full_rebuild(db) -> bool:
    """Detect legacy per-topic clusters (huge article counts) that need rebuilding."""
    from models import StoryCluster
    for cluster in db.query(StoryCluster).all():
        if len(cluster.articles) > 15:
            return True
    return False


def _is_db_empty(db) -> bool:
    from models import StoryCluster
    return db.query(StoryCluster).count() == 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from pipeline.sources import seed_sources
    db = next(get_db())
    seed_sources(db)
    needs_rebuild = _needs_full_rebuild(db)
    db_empty = _is_db_empty(db)
    db.close()

    if needs_rebuild:
        print("Legacy clusters detected - performing one-time full rebuild")

    # The in-process scheduler is unreliable on hosts that sleep when idle
    # (e.g. free tiers). There, disable it and trigger /api/fetch-news from an
    # external cron instead.
    if ENABLE_SCHEDULER:
        scheduler.add_job(scheduled_fetch, 'interval', hours=6, id='news_fetch')
        scheduler.start()
        print("Scheduler started - fetching news every 6 hours")
    else:
        print("In-process scheduler disabled (ENABLE_SCHEDULER=false)")

    # Decide whether to fetch on startup. Avoid doing this on every cold start
    # in production (expensive: RSS + LLM); only bootstrap an empty database.
    if FETCH_ON_STARTUP == "true":
        do_fetch = True
    elif FETCH_ON_STARTUP == "false":
        do_fetch = False
    else:  # "auto"
        do_fetch = db_empty or needs_rebuild

    if do_fetch:
        scheduled_fetch(full_recluster=needs_rebuild)
    else:
        print("Skipping startup fetch (database already populated)")

    yield

    if ENABLE_SCHEDULER and scheduler.running:
        scheduler.shutdown()

app = FastAPI(
    title="International Affairs API",
    description="News aggregation API comparing left and right perspectives on international affairs",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Netlify preview / branch deploy URLs (Part A before custom domain DNS)
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "International Affairs API",
        "version": "1.1.0",
        "endpoints": {
            "stories": "/api/stories",
            "stories_grouped": "/api/stories/grouped",
            "story_detail": "/api/stories/{id}",
            "sources": "/api/sources",
            "topics": "/api/topics",
            "search": "/api/search?q=",
            "daily_briefing": "/api/briefing/daily",
            "newsletter": "/api/newsletter/subscribe (POST)",
            "fetch_news": "/api/fetch-news (POST)",
        }
    }


@app.get("/api/stories", response_model=List[StoryListItem])
async def get_stories(
    topic: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get list of story clusters with perspective summaries.
    
    - **topic**: Filter by topic (trade, geopolitics, economy, security, climate)
    - **limit**: Maximum number of stories to return
    """
    return crud.get_stories(db, topic=topic, limit=limit)


@app.get("/api/stories/grouped")
async def get_stories_grouped(
    topic: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get stories grouped by time period (Today, This Week, This Month, Older).
    """
    return crud.get_stories_grouped(db, topic=topic)


@app.get("/api/stories/{story_id}", response_model=StoryDetail)
async def get_story(story_id: int, db: Session = Depends(get_db)):
    """
    Get detailed story with full comparison analysis.
    """
    story = crud.get_story_detail(db, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@app.get("/api/sources", response_model=List[SourceResponse])
async def get_sources(
    bias: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of news sources with bias ratings.
    
    - **bias**: Filter by bias category (left, centre, right)
    """
    return crud.get_sources(db, bias=bias)


@app.post("/api/fetch-news")
async def fetch_news(
    background_tasks: BackgroundTasks,
    x_fetch_token: Optional[str] = Header(default=None),
    token: Optional[str] = None,
    full: bool = False,
):
    """
    Trigger the news fetching pipeline (runs in background).

    If FETCH_TOKEN is configured, the caller must supply it via the
    `X-Fetch-Token` header or `?token=` query param. This stops the public
    internet from triggering the (LLM-billed) pipeline on your deployment.

    Pass `?full=true` to rebuild and re-classify every story (applies new
    topic rules, e.g. UK tagging, across all history). This is heavier and
    uses more LLM calls, so use it sparingly.
    """
    if FETCH_TOKEN and FETCH_TOKEN not in (x_fetch_token, token):
        raise HTTPException(status_code=401, detail="Invalid or missing fetch token")

    background_tasks.add_task(_run_pipeline_task, full)
    return {
        "message": "News fetch started in background"
        + (" (full rebuild)" if full else "")
    }


@app.get("/api/search", response_model=List[SearchResult])
async def search(q: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Search stories and articles by keyword.
    """
    return crud.search(db, query=q, limit=limit)


@app.get("/api/briefing/daily", response_model=DailyBriefing)
async def daily_briefing(db: Session = Depends(get_db)):
    """
    Get the daily briefing for the most recent day with stories.
    """
    return crud.get_daily_briefing(db)


@app.post("/api/newsletter/subscribe", response_model=SubscribeResponse)
async def subscribe_newsletter(signup: NewsletterSignup, db: Session = Depends(get_db)):
    """
    Subscribe an email address to the daily newsletter.
    """
    email = signup.email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please provide a valid email address")

    result = crud.subscribe_email(db, email)
    if result["already_subscribed"]:
        return SubscribeResponse(
            email=email, already_subscribed=True,
            message="You're already subscribed.",
        )
    return SubscribeResponse(
        email=email, already_subscribed=False,
        message="Successfully subscribed to the daily briefing.",
    )


@app.get("/api/topics")
async def get_topics():
    """
    Get list of available topics.
    """
    return {
        "topics": [
            {"id": "trade", "name": "Trade", "description": "Trade agreements, tariffs, and commerce"},
            {"id": "geopolitics", "name": "Geopolitics", "description": "International relations and diplomacy"},
            {"id": "economy", "name": "Economy", "description": "Global economics and finance"},
            {"id": "security", "name": "Security", "description": "Defence and military affairs"},
            {"id": "climate", "name": "Climate", "description": "Climate policy and energy"},
            {"id": "uk", "name": "UK", "description": "United Kingdom news and politics"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
