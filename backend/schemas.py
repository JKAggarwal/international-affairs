from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class SourceBase(BaseModel):
    name: str
    url: str
    rss_feed_url: Optional[str] = None
    bias_rating: Optional[float] = None
    bias_category: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None


class SourceResponse(SourceBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class ArticleBase(BaseModel):
    title: str
    url: str
    summary: Optional[str] = None
    topic: Optional[str] = None


class ArticleResponse(ArticleBase):
    id: int
    source_id: int
    source_name: str
    source_bias: str
    published_at: Optional[datetime] = None
    time_ago: str
    
    class Config:
        from_attributes = True


class PerspectiveSummary(BaseModel):
    label: str
    summary: str
    source_count: int


class ComparisonResponse(BaseModel):
    neutral_summary: Optional[str] = None
    left_framing: Optional[str] = None
    right_framing: Optional[str] = None
    agreements: List[str] = []
    disagreements: List[str] = []
    left_blind_spots: List[str] = []
    right_blind_spots: List[str] = []


class StoryListItem(BaseModel):
    id: int
    title: str
    topic: str
    neutral_summary: Optional[str] = None
    time_ago: str
    article_count: int
    left_perspective: PerspectiveSummary
    centre_perspective: PerspectiveSummary
    right_perspective: PerspectiveSummary
    agreement_preview: Optional[str] = None
    
    class Config:
        from_attributes = True


class StoryDetail(BaseModel):
    id: int
    title: str
    topic: str
    time_ago: str
    article_count: int
    comparison: ComparisonResponse
    articles: List[ArticleResponse]
    
    class Config:
        from_attributes = True


class NewsletterSignup(BaseModel):
    email: str


class SubscribeResponse(BaseModel):
    email: str
    already_subscribed: bool
    message: str


class SearchResult(BaseModel):
    type: str  # "story" or "article"
    id: int
    title: str
    topic: Optional[str] = None
    snippet: Optional[str] = None
    source_name: Optional[str] = None
    source_bias: Optional[str] = None
    url: Optional[str] = None  # external link for articles
    time_ago: Optional[str] = None


class BriefingItem(BaseModel):
    id: int
    title: str
    topic: str
    neutral_summary: Optional[str] = None
    left_count: int
    right_count: int
    centre_count: int


class DailyBriefing(BaseModel):
    date: str
    headline_count: int
    topics_covered: List[str]
    top_stories: List[BriefingItem]
    consensus: List[str]      # stories where left & right broadly agree
    most_divisive: List[str]  # stories with the sharpest framing split
