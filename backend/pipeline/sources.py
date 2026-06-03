from sqlalchemy.orm import Session
from models import Source

SOURCES = [
    {
        "name": "The Guardian",
        "url": "https://www.theguardian.com",
        "rss_feed_url": "https://www.theguardian.com/world/rss",
        "bias_rating": -3.0,
        "bias_category": "left",
        "country": "United Kingdom",
        "description": "British daily newspaper known for progressive editorial stance and extensive international coverage."
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com",
        "rss_feed_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "bias_rating": -2.5,
        "bias_category": "left",
        "country": "Qatar",
        "description": "International news network offering perspectives often underrepresented in Western media."
    },
    {
        "name": "New York Times",
        "url": "https://www.nytimes.com",
        "rss_feed_url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "bias_rating": -2.0,
        "bias_category": "centre-left",
        "country": "United States",
        "description": "Leading American newspaper with extensive foreign bureaux and international reporting."
    },
    {
        "name": "The Atlantic",
        "url": "https://www.theatlantic.com",
        "rss_feed_url": "https://www.theatlantic.com/feed/all/",
        "bias_rating": -1.5,
        "bias_category": "centre-left",
        "country": "United States",
        "description": "American magazine covering politics, foreign affairs, and culture with in-depth analysis."
    },
    {
        "name": "NPR",
        "url": "https://www.npr.org",
        "rss_feed_url": "https://feeds.npr.org/1004/rss.xml",
        "bias_rating": -1.5,
        "bias_category": "centre-left",
        "country": "United States",
        "description": "American public broadcaster providing in-depth national and world coverage."
    },
    {
        "name": "BBC News",
        "url": "https://www.bbc.com/news",
        "rss_feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bias_rating": 0.0,
        "bias_category": "centre",
        "country": "United Kingdom",
        "description": "British public broadcaster with extensive global newsgathering and neutral reporting."
    },
    {
        "name": "Deutsche Welle",
        "url": "https://www.dw.com",
        "rss_feed_url": "https://rss.dw.com/rdf/rss-en-world",
        "bias_rating": 0.0,
        "bias_category": "centre",
        "country": "Germany",
        "description": "Germany's international broadcaster offering a European perspective on world affairs."
    },
    {
        "name": "France 24",
        "url": "https://www.france24.com/en/",
        "rss_feed_url": "https://www.france24.com/en/rss",
        "bias_rating": 0.0,
        "bias_category": "centre",
        "country": "France",
        "description": "French international news network covering global affairs in English."
    },
    {
        "name": "Financial Times",
        "url": "https://www.ft.com",
        "rss_feed_url": "https://www.ft.com/world?format=rss",
        "bias_rating": 0.5,
        "bias_category": "centre",
        "country": "United Kingdom",
        "description": "Business newspaper with strong international coverage and economically-focused analysis."
    },
    {
        "name": "The Economist",
        "url": "https://www.economist.com",
        "rss_feed_url": "https://www.economist.com/international/rss.xml",
        "bias_rating": 0.5,
        "bias_category": "centre",
        "country": "United Kingdom",
        "description": "Weekly magazine covering international affairs with classical liberal perspective."
    },
    {
        "name": "New York Post",
        "url": "https://nypost.com",
        "rss_feed_url": "https://nypost.com/world-news/feed/",
        "bias_rating": 2.5,
        "bias_category": "centre-right",
        "country": "United States",
        "description": "American tabloid with a conservative editorial slant and wide world-news coverage."
    },
    {
        "name": "The Telegraph",
        "url": "https://www.telegraph.co.uk",
        "rss_feed_url": "https://www.telegraph.co.uk/rss.xml",
        "bias_rating": 3.0,
        "bias_category": "right",
        "country": "United Kingdom",
        "description": "British broadsheet with conservative editorial stance and strong foreign affairs section."
    },
    {
        "name": "National Review",
        "url": "https://www.nationalreview.com",
        "rss_feed_url": "https://www.nationalreview.com/feed/",
        "bias_rating": 3.5,
        "bias_category": "right",
        "country": "United States",
        "description": "American conservative magazine covering politics and international affairs."
    },
    {
        "name": "The Daily Wire",
        "url": "https://www.dailywire.com",
        "rss_feed_url": "https://www.dailywire.com/feeds/rss.xml",
        "bias_rating": 4.0,
        "bias_category": "right",
        "country": "United States",
        "description": "American conservative news and commentary site covering politics and world affairs."
    },
]

# Sources that were previously seeded but whose public RSS feeds are no longer
# available. They are deactivated on startup so the pipeline doesn't waste time
# on dead feeds while keeping their historical articles in the database.
DEPRECATED_SOURCE_NAMES = ["Reuters", "Associated Press", "Wall Street Journal", "The Spectator"]


def seed_sources(db: Session):
    """Seed the database with initial sources and refresh known feed URLs."""
    for source_data in SOURCES:
        existing = db.query(Source).filter(Source.name == source_data["name"]).first()
        if existing:
            # Keep feed URLs and metadata in sync with the latest definitions.
            existing.rss_feed_url = source_data["rss_feed_url"]
            existing.bias_rating = source_data["bias_rating"]
            existing.bias_category = source_data["bias_category"]
            existing.is_active = True
        else:
            db.add(Source(**source_data))

    # Deactivate sources whose feeds no longer work.
    for name in DEPRECATED_SOURCE_NAMES:
        dead = db.query(Source).filter(Source.name == name).first()
        if dead:
            dead.is_active = False

    db.commit()
    active = db.query(Source).filter(Source.is_active == True).count()
    print(f"Seeded sources ({active} active)")
