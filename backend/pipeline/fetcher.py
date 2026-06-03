from dotenv import load_dotenv
load_dotenv()  # so OPENAI_API_KEY is available when run as `python -m pipeline.fetcher`

import feedparser
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

import sys
sys.path.append('..')

from database import SessionLocal
from models import Source, Article, StoryCluster, Comparison, cluster_articles as cluster_articles_table
from .clustering import ArticleLike, cluster_articles, is_publishable
from . import analysis

USER_AGENT = "Mozilla/5.0 (compatible; InternationalAffairsBot/1.0; +https://internationalaffairs.example)"

TOPIC_KEYWORDS = {
    "trade": ["trade", "tariff", "export", "import", "wto", "commerce", "customs", "quota", "trade war", "trade deal", "trade agreement", "supply chain", "sanction"],
    "geopolitics": ["diplomatic", "diplomacy", "ambassador", "foreign minister", "summit", "alliance", "nato", "united nations", "bilateral", "territorial", "border", "treaty", "election", "president", "parliament", "regime"],
    "economy": ["economy", "economic", "gdp", "inflation", "interest rate", "federal reserve", "central bank", "imf", "world bank", "recession", "growth", "currency", "markets", "stocks", "investment", "debt"],
    "security": ["military", "defence", "defense", "army", "navy", "missile", "nuclear", "weapons", "troops", "conflict", "security", "war", "airstrike", "offensive", "ceasefire", "insurgent", "militant", "hostage"],
    "climate": ["climate", "carbon", "emissions", "renewable", "energy", "paris agreement", "environmental", "sustainability", "oil", "gas", "fossil", "pipeline"],
}

# Content that isn't international affairs. If any of these appear and the
# article doesn't otherwise score, it's dropped (classified "general").
EXCLUDE_KEYWORDS = [
    "champions league", "premier league", "football", "soccer", "tennis",
    "cricket", "rugby", "golf", "olympic", "match", "fixture", "transfer window",
    "film", "movie", "tv series", "celebrity", "fashion", "recipe", "horoscope",
    "box office", "album", "concert", "festival", "royal wedding", "week in pictures",
    "quiz", "puzzle", "crossword", "obituary", "gossip",
]


def classify_topic(text: str) -> str:
    """Classify an article's topic based on keyword frequency."""
    text_lower = text.lower()

    affairs_score = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            affairs_score[topic] = score

    # Drop sports/entertainment unless there's a strong affairs signal.
    if any(kw in text_lower for kw in EXCLUDE_KEYWORDS):
        if not affairs_score or max(affairs_score.values()) < 2:
            return "general"

    if affairs_score:
        return max(affairs_score, key=affairs_score.get)
    return "general"


def clean_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)


def parse_date(entry) -> Optional[datetime]:
    """Use feedparser's parsed time struct when available."""
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime(*value[:6])
            except (TypeError, ValueError):
                continue
    return None


def fetch_source_articles(source: Source) -> List[Dict]:
    """Fetch and normalise articles from a single source's RSS feed."""
    if not source.rss_feed_url:
        return []

    try:
        feed = feedparser.parse(source.rss_feed_url, agent=USER_AGENT)
        articles = []

        for entry in feed.entries[:25]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            published = parse_date(entry)

            if title and url:
                articles.append({
                    "source_id": source.id,
                    "title": title,
                    "url": url,
                    "summary": summary[:600] if summary else None,
                    "published_at": published,
                    "topic": classify_topic(f"{title} {summary}"),
                })

        print(f"  Fetched {len(articles)} articles from {source.name}")
        return articles

    except Exception as e:  # noqa: BLE001
        print(f"  Error fetching {source.name}: {e}")
        return []


def save_articles(db: Session, articles: List[Dict]) -> int:
    """Save articles, skipping duplicate URLs."""
    saved = 0
    seen_urls = set()
    for data in articles:
        url = data["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if not db.query(Article).filter(Article.url == url).first():
            db.add(Article(**data))
            saved += 1
    db.commit()
    return saved


def _effective_date(article: Article) -> datetime:
    return article.published_at or article.scraped_at or article.created_at or datetime.utcnow()


def _choose_title(members: List[Article]) -> str:
    """Pick a representative headline: prefer a centre source, else longest."""
    centre = [m for m in members if m.source.bias_category == "centre"]
    pool = centre or members
    return max(pool, key=lambda m: len(m.title or "")).title


def _delete_cluster(db: Session, cluster: StoryCluster):
    if cluster.comparison:
        db.delete(cluster.comparison)
    db.execute(
        cluster_articles_table.delete().where(
            cluster_articles_table.c.cluster_id == cluster.id
        )
    )
    db.delete(cluster)


def recluster(db: Session, full: bool = False, window_hours: int = 72) -> int:
    """Rebuild story clusters and comparisons.

    - full=True rebuilds every cluster from all articles (use once for migration).
    - Otherwise only clusters created within the rolling window are rebuilt, so
      older history stays frozen and stable.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=window_hours)

    if full:
        # Re-run topic classification so updated rules (e.g. excluding sport)
        # apply to articles that were stored under the old classifier.
        for a in db.query(Article).all():
            a.topic = classify_topic(f"{a.title} {a.summary or ''}")
        db.commit()
        for cluster in db.query(StoryCluster).all():
            _delete_cluster(db, cluster)
        db.commit()
        candidate_articles = db.query(Article).filter(Article.topic != "general").all()
    else:
        for cluster in db.query(StoryCluster).filter(StoryCluster.created_at >= cutoff).all():
            _delete_cluster(db, cluster)
        db.commit()
        candidate_articles = (
            db.query(Article)
            .filter(Article.created_at >= cutoff, Article.topic != "general")
            .all()
        )

    # Keep articles already locked into a frozen (older) cluster out of the mix.
    frozen_article_ids = {
        row.article_id
        for row in db.query(cluster_articles_table.c.article_id).all()
    }
    pool = [a for a in candidate_articles if a.id not in frozen_article_ids]

    if not pool:
        return 0

    by_id = {a.id: a for a in pool}
    items = [
        ArticleLike(
            id=a.id,
            title=a.title or "",
            summary=a.summary or "",
            topic=a.topic or "general",
            bias_category=a.source.bias_category or "centre",
        )
        for a in pool
    ]

    clusters = cluster_articles(items)
    created = 0

    for cluster in clusters:
        if not is_publishable(cluster):
            continue

        members = [by_id[i] for i in cluster.article_ids]
        source_lookup = {m.id: m.source.name for m in members}

        story = StoryCluster(
            title=_choose_title(members),
            topic=cluster.topic or "general",
            created_at=max(_effective_date(m) for m in members),
        )
        story.articles = members
        db.add(story)
        db.flush()  # assign story.id

        result = analysis.generate_comparison(cluster.members, source_lookup)
        story.neutral_summary = result.get("neutral_summary")

        db.add(Comparison(
            cluster_id=story.id,
            neutral_summary=result.get("neutral_summary"),
            left_framing=result.get("left_framing"),
            right_framing=result.get("right_framing"),
            agreements=result.get("agreements", []),
            disagreements=result.get("disagreements", []),
            left_blind_spots=result.get("left_blind_spots", []),
            right_blind_spots=result.get("right_blind_spots", []),
        ))
        created += 1

    db.commit()
    return created


def run_pipeline(full_recluster: bool = False):
    """Fetch from all active sources, then (re)cluster and analyse."""
    print("\n" + "=" * 50)
    print("Starting news fetch pipeline...")
    print("=" * 50)

    db = SessionLocal()
    try:
        sources = db.query(Source).filter(Source.is_active == True).all()
        print(f"\nFetching from {len(sources)} active sources...")

        all_articles = []
        for source in sources:
            all_articles.extend(fetch_source_articles(source))

        saved = save_articles(db, all_articles)
        print(f"\nSaved {saved} new articles")

        print("\nClustering stories and generating comparisons...")
        created = recluster(db, full=full_recluster)
        print(f"Built {created} story clusters")

        print("\n" + "=" * 50)
        print("Pipeline complete!")
        print("=" * 50 + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"Pipeline error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # `python -m pipeline.fetcher --full` does a one-off full rebuild.
    full = "--full" in sys.argv
    run_pipeline(full_recluster=full)
