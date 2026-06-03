# International Affairs

A news aggregation platform that analyses international affairs coverage from across the political spectrum, showing how left and right perspectives frame the same stories differently.

## Overview

This platform:
- Aggregates news from 14 established sources across the political spectrum
- Groups related articles into individual story clusters (TF-IDF + entity matching)
- Compares how left-leaning and right-leaning sources cover the same events
- Highlights agreements, disagreements and each side's blind spots
- Produces a daily briefing, full-text search and a time-grouped story archive
- Auto-refreshes every 6 hours via a built-in scheduler

## Project Structure

```
international-affairs/
├── website/                    # Frontend (HTML/CSS/JS)
│   ├── index.html              # Homepage with story listings
│   ├── story.html              # Individual story comparison view
│   ├── sources.html            # Source directory
│   ├── about.html              # About page
│   ├── logo.jpeg               # Site logo
│   ├── css/
│   │   └── styles.css          # All styling
│   └── js/
│       └── app.js              # Frontend JavaScript (API integration)
│
├── backend/                    # Backend API (Python/FastAPI)
│   ├── main.py                 # FastAPI application
│   ├── database.py             # Database connection
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── crud.py                 # Database operations (stories, search, briefing, subscribers)
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── pipeline/
│       ├── __init__.py
│       ├── sources.py          # News source definitions + feed health
│       ├── nlp.py              # Dependency-free text utils (TF-IDF, entities)
│       ├── clustering.py       # Groups articles into individual stories
│       ├── analysis.py         # Left/right comparison engine (heuristic + optional LLM)
│       └── fetcher.py          # RSS fetching, clustering & analysis orchestration
│
├── website-concept.md          # Detailed concept document
├── action-plan.md              # Implementation roadmap
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.9+
- pip (Python package manager)

### 1. Set Up the Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the API server
python main.py
```

The API will be running at `http://localhost:8000`

### 2. Start the Frontend

Open a new terminal:

```bash
# Navigate to website directory
cd website

# Start a simple HTTP server
python3 -m http.server 8080
```

The website will be running at `http://localhost:8080`

### 3. Fetch News

With both servers running, you can fetch news in two ways:

**Option A: Via API endpoint**
```bash
curl -X POST http://localhost:8000/api/fetch-news
```

**Option B: Run the pipeline directly**
```bash
cd backend
python -m pipeline.fetcher
```

**Option C: Click the button on the website**
If no stories are loaded, a "Fetch News Now" button appears.

### 4. View the Site

Open `http://localhost:8080` in your browser to see the platform with real news data.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info and available endpoints |
| `/api/stories` | GET | List all story clusters |
| `/api/stories?topic={topic}` | GET | Filter stories by topic |
| `/api/stories/grouped` | GET | Stories grouped by time period (Today, This Week, …) |
| `/api/stories/{id}` | GET | Get single story with full comparison |
| `/api/sources` | GET | List all news sources |
| `/api/sources?bias={bias}` | GET | Filter sources by bias (left/centre/right) |
| `/api/topics` | GET | List available topics |
| `/api/search?q={query}` | GET | Search stories and articles |
| `/api/briefing/daily` | GET | Daily briefing (top stories, consensus, divisive) |
| `/api/fetch-news` | POST | Trigger news fetching pipeline |
| `/api/newsletter/subscribe` | POST | Subscribe an email to the newsletter (stored, de-duplicated) |

### Example API Calls

```bash
# Get all stories
curl http://localhost:8000/api/stories

# Get trade stories only
curl http://localhost:8000/api/stories?topic=trade

# Get story details
curl http://localhost:8000/api/stories/1

# Get all sources
curl http://localhost:8000/api/sources

# Get left-leaning sources only
curl http://localhost:8000/api/sources?bias=left
```

---

## News Sources

The platform aggregates from these sources:

### Left / Centre-Left
| Source | Country | Bias Rating |
|--------|---------|-------------|
| The Guardian | UK | -3.0 |
| Al Jazeera | Qatar | -2.5 |
| New York Times | US | -2.0 |
| The Atlantic | US | -1.5 |
| NPR | US | -1.5 |

### Centre
| Source | Country | Bias Rating |
|--------|---------|-------------|
| BBC News | UK | 0.0 |
| Deutsche Welle | Germany | 0.0 |
| France 24 | France | 0.0 |
| Financial Times | UK | +0.5 |
| The Economist | UK | +0.5 |

### Centre-Right / Right
| Source | Country | Bias Rating |
|--------|---------|-------------|
| New York Post | US | +2.5 |
| The Telegraph | UK | +3.0 |
| National Review | US | +3.5 |
| The Daily Wire | US | +4.0 |

> Sources whose public RSS feeds have been discontinued (Reuters, Associated Press, Wall Street Journal, The Spectator) are automatically deactivated on startup, so the pipeline only polls feeds that work. They remain in the database for historical articles.

---

## Topics

Stories are classified into these categories:
- **Trade** - Tariffs, trade agreements, commerce
- **Geopolitics** - International relations, diplomacy
- **Economy** - Central banks, currencies, economic policy
- **Security** - Defence, military affairs, conflicts
- **Climate** - Climate policy, energy transition

Sport, entertainment and other non-affairs content is filtered out during classification.

---

## How It Works

The pipeline (`backend/pipeline/`) runs in four stages each cycle:

1. **Fetch** (`fetcher.py`) — pulls articles from every active RSS feed, strips HTML, parses dates and classifies each article's topic.
2. **Cluster** (`clustering.py`) — groups articles that cover the *same* story. It builds a lightweight TF-IDF model (`nlp.py`), then greedily merges articles by cosine similarity blended with shared proper-noun (entity) overlap. Same-topic + shared-entity is required to merge, which prevents unrelated stories collapsing into one blob. A story is published once at least two sources cover it.
3. **Analyse** (`analysis.py`) — for each cluster it generates the left/right comparison: representative framing per side, shared themes (agreements), distinctive emphasis (disagreements) and what each side underplays (blind spots).
4. **Persist** — clusters and comparisons are written to the database and surfaced through the API.

### Comparison engine: heuristic vs LLM

- **Heuristic (default, no key needed):** derives framing, agreements and blind spots from the vocabulary and named entities each side emphasises. Works fully offline.
- **LLM (optional):** set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) in `.env` to generate richer comparisons via the OpenAI API. The pipeline automatically falls back to the heuristic on any error, so the site never breaks if the key is missing or a request fails.

> Note: a fair left/right comparison only appears when both sides actually cover a story. Where only one side has reported, the comparison says so honestly rather than inventing the other side.

---

## Database

The backend uses SQLite by default (no setup required). The database file `international_affairs.db` is created automatically in the `backend/` directory.

### Database Schema

```
sources          → News source definitions
articles         → Individual articles fetched from RSS
story_clusters   → Groups of related articles (one real-world story each)
comparisons      → Left/right analysis for each cluster
cluster_articles → Many-to-many relationship (article ↔ cluster)
subscribers      → Newsletter email subscribers (unique, de-duplicated)
```

### Switching to PostgreSQL

For production, you can switch to PostgreSQL:

1. Install PostgreSQL and create a database:
   ```bash
   createdb international_affairs
   ```

2. Update `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost/international_affairs
   ```

3. Install the PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

---

## Scheduled Fetching

The backend already runs an **APScheduler** job that fetches news and rebuilds
recent clusters **every 6 hours**, plus an initial fetch on startup — no cron
needed. This is wired up in `main.py`'s `lifespan` handler.

The first time it detects legacy/oversized clusters it performs a one-time full
rebuild; after that it only rebuilds clusters inside a rolling 72-hour window so
older history stays stable. To force a full rebuild manually:

```bash
cd backend
python -m pipeline.fetcher --full
```

To change the interval, edit the `scheduler.add_job(..., hours=6)` line in `main.py`.

---

## Development

### Running in Development Mode

Backend with auto-reload:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### API Documentation

FastAPI provides automatic documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Adding New Sources

Edit `backend/pipeline/sources.py`:

```python
SOURCES = [
    # Add new source
    {
        "name": "BBC News",
        "url": "https://www.bbc.com/news",
        "rss_feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bias_rating": 0.0,
        "bias_category": "centre",
        "country": "United Kingdom",
        "description": "British public broadcaster"
    },
    # ... existing sources
]
```

Then restart the server to seed the new source.

---

## Future Enhancements

See `action-plan.md` for the full roadmap.

Already implemented:
- [x] Per-story clustering (TF-IDF + entity overlap)
- [x] Left/right comparison engine (heuristic, with optional OpenAI LLM)
- [x] Scheduled auto-refresh every 6 hours
- [x] Time-grouped story history
- [x] Daily briefing endpoint + homepage section
- [x] Full-text search across stories and articles
- [x] Persisted, de-duplicated newsletter subscribers

Key upcoming features:
- [ ] Sentence-embedding clustering for even tighter story grouping
- [ ] Outbound email delivery for the daily briefing
- [ ] User accounts and personalisation
- [ ] Browser extension and mobile app
- [ ] Sentiment / framing-trend dashboard

---

## Troubleshooting

### "No stories found"
Run the news fetcher: `curl -X POST http://localhost:8000/api/fetch-news`

### CORS errors in browser
Make sure you're accessing the frontend via `http://localhost:8080`, not by opening the file directly.

### RSS feeds failing
Some sources may block or rate-limit requests. Check the console output when running the fetcher.

### Database errors
Delete `backend/international_affairs.db` and restart the server to recreate the database.

---

## License

MIT License - See LICENSE file for details.

---

## Contact

For questions or feedback, reach out at hello@internationalaffairs.com
