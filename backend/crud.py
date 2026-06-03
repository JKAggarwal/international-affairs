from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from models import Source, Article, StoryCluster, Comparison, Subscriber
from schemas import (
    StoryListItem, StoryDetail, ArticleResponse, SourceResponse,
    PerspectiveSummary, ComparisonResponse, SearchResult, BriefingItem,
    DailyBriefing,
)
from datetime import datetime, timedelta
from typing import List, Optional


NO_LEFT = "No left-leaning sources have covered this story yet."
NO_RIGHT = "No right-leaning sources have covered this story yet."
NO_CENTRE = "Factual reporting from neutral sources"


def get_time_ago(dt: datetime) -> str:
    if not dt:
        return "Recently"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%B %d, %Y")


def get_sources(db: Session, bias: Optional[str] = None) -> List[SourceResponse]:
    query = db.query(Source).filter(Source.is_active == True)
    
    if bias and bias != "all":
        if bias == "left":
            query = query.filter(Source.bias_category.in_(["left", "centre-left"]))
        elif bias == "centre":
            query = query.filter(Source.bias_category == "centre")
        elif bias == "right":
            query = query.filter(Source.bias_category.in_(["right", "centre-right"]))
    
    sources = query.order_by(Source.bias_rating).all()
    return [SourceResponse.model_validate(s) for s in sources]


def get_stories(db: Session, topic: Optional[str] = None, limit: int = 20) -> List[StoryListItem]:
    query = db.query(StoryCluster).order_by(desc(StoryCluster.created_at))
    
    if topic and topic != "all":
        query = query.filter(StoryCluster.topic == topic)
    
    clusters = query.limit(limit).all()
    
    stories = []
    for cluster in clusters:
        articles = cluster.articles
        
        left_articles = [a for a in articles if a.source.bias_category in ["left", "centre-left"]]
        centre_articles = [a for a in articles if a.source.bias_category == "centre"]
        right_articles = [a for a in articles if a.source.bias_category in ["right", "centre-right"]]
        
        comparison = cluster.comparison
        
        stories.append(_story_list_item(cluster, articles, left_articles, centre_articles, right_articles))
    
    return stories


def _story_list_item(cluster, articles, left_articles, centre_articles, right_articles) -> StoryListItem:
    comparison = cluster.comparison
    left_summary = (comparison.left_framing if comparison else None) or NO_LEFT
    right_summary = (comparison.right_framing if comparison else None) or NO_RIGHT
    return StoryListItem(
        id=cluster.id,
        title=cluster.title,
        topic=cluster.topic or "General",
        neutral_summary=(comparison.neutral_summary if comparison else None) or cluster.neutral_summary,
        time_ago=get_time_ago(cluster.created_at),
        article_count=len(articles),
        left_perspective=PerspectiveSummary(label="Left", summary=left_summary, source_count=len(left_articles)),
        centre_perspective=PerspectiveSummary(label="Centre", summary=NO_CENTRE, source_count=len(centre_articles)),
        right_perspective=PerspectiveSummary(label="Right", summary=right_summary, source_count=len(right_articles)),
        agreement_preview=comparison.agreements[0] if comparison and comparison.agreements else None,
    )


def get_story_detail(db: Session, story_id: int) -> Optional[StoryDetail]:
    cluster = db.query(StoryCluster).filter(StoryCluster.id == story_id).first()
    
    if not cluster:
        return None
    
    articles = []
    for article in cluster.articles:
        articles.append(ArticleResponse(
            id=article.id,
            title=article.title,
            url=article.url,
            summary=article.summary,
            topic=article.topic,
            source_id=article.source_id,
            source_name=article.source.name,
            source_bias=article.source.bias_category,
            published_at=article.published_at,
            time_ago=get_time_ago(article.published_at)
        ))
    
    comparison = cluster.comparison
    comparison_response = ComparisonResponse(
        neutral_summary=comparison.neutral_summary if comparison else cluster.neutral_summary,
        left_framing=comparison.left_framing if comparison else None,
        right_framing=comparison.right_framing if comparison else None,
        agreements=comparison.agreements if comparison and comparison.agreements else [],
        disagreements=comparison.disagreements if comparison and comparison.disagreements else [],
        left_blind_spots=comparison.left_blind_spots if comparison and comparison.left_blind_spots else [],
        right_blind_spots=comparison.right_blind_spots if comparison and comparison.right_blind_spots else []
    )
    
    return StoryDetail(
        id=cluster.id,
        title=cluster.title,
        topic=cluster.topic or "General",
        time_ago=get_time_ago(cluster.created_at),
        article_count=len(articles),
        comparison=comparison_response,
        articles=sorted(articles, key=lambda a: (
            0 if a.source_bias in ["left", "centre-left"] else 
            1 if a.source_bias == "centre" else 2
        ))
    )


def get_article(db: Session, article_id: int) -> Optional[ArticleResponse]:
    article = db.query(Article).filter(Article.id == article_id).first()
    
    if not article:
        return None
    
    return ArticleResponse(
        id=article.id,
        title=article.title,
        url=article.url,
        summary=article.summary,
        topic=article.topic,
        source_id=article.source_id,
        source_name=article.source.name,
        source_bias=article.source.bias_category,
        published_at=article.published_at,
        time_ago=get_time_ago(article.published_at)
    )


def get_stories_grouped(db: Session, topic: Optional[str] = None) -> dict:
    """Get stories grouped by time period."""
    from datetime import date
    
    query = db.query(StoryCluster).order_by(desc(StoryCluster.created_at))
    
    if topic and topic != "all":
        query = query.filter(StoryCluster.topic == topic)
    
    clusters = query.all()
    
    today = date.today()
    april_6 = date(2026, 4, 6)
    
    groups = {
        "today": [],
        "yesterday": [],
        "this_week": [],
        "last_week": [],
        "this_month": [],
        "older": []
    }
    
    for cluster in clusters:
        story = cluster_to_story_item(cluster)
        cluster_date = cluster.created_at.date()
        
        days_ago = (today - cluster_date).days
        
        if cluster_date < april_6:
            continue
        elif days_ago == 0:
            groups["today"].append(story)
        elif days_ago == 1:
            groups["yesterday"].append(story)
        elif days_ago <= 7:
            groups["this_week"].append(story)
        elif days_ago <= 14:
            groups["last_week"].append(story)
        elif days_ago <= 30:
            groups["this_month"].append(story)
        else:
            groups["older"].append(story)
    
    return {
        "sections": [
            {"title": "Today's Stories", "key": "today", "stories": groups["today"]},
            {"title": "Yesterday", "key": "yesterday", "stories": groups["yesterday"]},
            {"title": "This Week", "key": "this_week", "stories": groups["this_week"]},
            {"title": "Last Week", "key": "last_week", "stories": groups["last_week"]},
            {"title": "This Month", "key": "this_month", "stories": groups["this_month"]},
            {"title": "Since April 6", "key": "older", "stories": groups["older"]},
        ],
        "total_stories": len(clusters),
        "last_updated": datetime.utcnow().isoformat()
    }


def subscribe_email(db: Session, email: str) -> dict:
    """Add a newsletter subscriber, returning whether they already existed."""
    email = email.strip().lower()
    existing = db.query(Subscriber).filter(Subscriber.email == email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.commit()
        return {"already_subscribed": True}
    db.add(Subscriber(email=email))
    db.commit()
    return {"already_subscribed": False}


def search(db: Session, query: str, limit: int = 20) -> List[SearchResult]:
    """Search story clusters and articles by title/summary."""
    q = (query or "").strip()
    if not q:
        return []

    like = f"%{q}%"
    results: List[SearchResult] = []

    clusters = (
        db.query(StoryCluster)
        .filter(or_(StoryCluster.title.ilike(like), StoryCluster.neutral_summary.ilike(like)))
        .order_by(desc(StoryCluster.created_at))
        .limit(limit)
        .all()
    )
    for c in clusters:
        results.append(SearchResult(
            type="story",
            id=c.id,
            title=c.title,
            topic=c.topic,
            snippet=(c.neutral_summary or "")[:160] or None,
            time_ago=get_time_ago(c.created_at),
        ))

    remaining = limit - len(results)
    if remaining > 0:
        articles = (
            db.query(Article)
            .filter(or_(Article.title.ilike(like), Article.summary.ilike(like)))
            .order_by(desc(Article.published_at))
            .limit(remaining)
            .all()
        )
        for a in articles:
            results.append(SearchResult(
                type="article",
                id=a.id,
                title=a.title,
                topic=a.topic,
                snippet=(a.summary or "")[:160] or None,
                source_name=a.source.name,
                source_bias=a.source.bias_category,
                url=a.url,
                time_ago=get_time_ago(a.published_at),
            ))

    return results


def get_daily_briefing(db: Session) -> DailyBriefing:
    """Build a briefing from the most recent day that has stories."""
    latest = db.query(StoryCluster).order_by(desc(StoryCluster.created_at)).first()
    if not latest:
        return DailyBriefing(
            date=datetime.utcnow().strftime("%B %d, %Y"),
            headline_count=0,
            topics_covered=[],
            top_stories=[],
            consensus=[],
            most_divisive=[],
        )

    day = latest.created_at.date()
    clusters = (
        db.query(StoryCluster)
        .filter(StoryCluster.created_at >= datetime(day.year, day.month, day.day))
        .order_by(desc(StoryCluster.created_at))
        .all()
    )

    items: List[BriefingItem] = []
    both_sided = []  # (cluster, agreements_count, distinct_count)

    for c in clusters:
        articles = c.articles
        left = sum(1 for a in articles if a.source.bias_category in ["left", "centre-left"])
        centre = sum(1 for a in articles if a.source.bias_category == "centre")
        right = sum(1 for a in articles if a.source.bias_category in ["right", "centre-right"])

        items.append(BriefingItem(
            id=c.id,
            title=c.title,
            topic=c.topic or "general",
            neutral_summary=c.neutral_summary,
            left_count=left,
            right_count=right,
            centre_count=centre,
        ))

        if left and right and c.comparison:
            agreements = len(c.comparison.agreements or [])
            disagreements = len(c.comparison.disagreements or [])
            both_sided.append((c, agreements, disagreements))

    items.sort(key=lambda i: (i.left_count + i.centre_count + i.right_count), reverse=True)

    consensus = [c.title for c, agr, dis in sorted(both_sided, key=lambda t: -t[1])[:3]]
    most_divisive = [c.title for c, agr, dis in sorted(both_sided, key=lambda t: -t[2])[:3]]
    topics = sorted({i.topic for i in items if i.topic and i.topic != "general"})

    return DailyBriefing(
        date=day.strftime("%B %d, %Y"),
        headline_count=len(items),
        topics_covered=topics,
        top_stories=items[:6],
        consensus=consensus,
        most_divisive=most_divisive,
    )


def cluster_to_story_item(cluster: StoryCluster) -> StoryListItem:
    """Convert a cluster to a StoryListItem."""
    articles = cluster.articles
    left_articles = [a for a in articles if a.source.bias_category in ["left", "centre-left"]]
    centre_articles = [a for a in articles if a.source.bias_category == "centre"]
    right_articles = [a for a in articles if a.source.bias_category in ["right", "centre-right"]]
    return _story_list_item(cluster, articles, left_articles, centre_articles, right_articles)
