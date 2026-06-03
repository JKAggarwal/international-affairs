from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

cluster_articles = Table(
    'cluster_articles',
    Base.metadata,
    Column('cluster_id', Integer, ForeignKey('story_clusters.id'), primary_key=True),
    Column('article_id', Integer, ForeignKey('articles.id'), primary_key=True)
)


class Source(Base):
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(500), nullable=False)
    rss_feed_url = Column(String(500))
    bias_rating = Column(Float)  # -5.0 (far left) to +5.0 (far right)
    bias_category = Column(String(20))  # left, centre-left, centre, centre-right, right
    country = Column(String(100))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    articles = relationship("Article", back_populates="source")


class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    summary = Column(Text)
    full_text = Column(Text)
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    topic = Column(String(100))
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("Source", back_populates="articles")
    clusters = relationship("StoryCluster", secondary=cluster_articles, back_populates="articles")


class StoryCluster(Base):
    __tablename__ = 'story_clusters'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    topic = Column(String(100))
    neutral_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    articles = relationship("Article", secondary=cluster_articles, back_populates="clusters")
    comparison = relationship("Comparison", back_populates="cluster", uselist=False)


class Subscriber(Base):
    __tablename__ = 'subscribers'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Comparison(Base):
    __tablename__ = 'comparisons'
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey('story_clusters.id'), unique=True)
    neutral_summary = Column(Text)
    left_framing = Column(Text)
    right_framing = Column(Text)
    agreements = Column(JSON)  # List of strings
    disagreements = Column(JSON)  # List of strings
    left_blind_spots = Column(JSON)
    right_blind_spots = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    cluster = relationship("StoryCluster", back_populates="comparison")
