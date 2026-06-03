# International Affairs News Comparison Platform

## Concept Overview

A platform that aggregates international affairs news from across the political spectrum, presenting side-by-side analysis of how left-leaning and right-leaning publications cover the same stories.

**Unique Selling Point:** Takes articles from both the left and right of the political spectrum and analyses how the two positions compare on international affairs issues including trade, geopolitics, investment, and economies.

---

## Part 1: Website Content & Features

### Core Content Sections

#### 1. Topic Categories
- Trade & Tariffs
- Geopolitics & Diplomacy
- Foreign Investment & Capital Flows
- Macroeconomics & Currencies
- Defence & Security
- Climate & Energy Policy
- Migration & Demographics
- International Institutions (UN, IMF, WTO, etc.)

#### 2. Main Feature: "Perspective Comparison"
- Side-by-side article summaries on the same story
- Left source | Centre (facts) | Right source format
- Highlighted areas of agreement and disagreement
- Key framing differences (language, emphasis, omissions)

#### 3. Daily/Weekly Briefings
- "The Story" - neutral factual summary
- "From the Left" - aggregated left-leaning analysis
- "From the Right" - aggregated right-leaning analysis
- "The Blind Spots" - what each side tends to ignore

#### 4. Source Library
Curated list of publications with political leaning ratings:

| Leaning | Example Sources |
|---------|-----------------|
| Left | The Guardian, Jacobin, The Nation, Al Jazeera |
| Centre | Reuters, AP, Financial Times, The Economist |
| Right | The Telegraph, Wall Street Journal, National Review, The Spectator |

#### 5. Interactive Features
- "Bias Meter" showing coverage intensity by political leaning
- Reader polls on which perspective they found more compelling
- Comment sections with verified political self-identification
- Newsletter with customisable political balance settings

---

## Part 2: Technical Requirements

### Frontend

| Component | Technology Options |
|-----------|-------------------|
| Framework | React, Vue.js, or Next.js |
| Styling | Tailwind CSS, styled-components |
| State Management | Redux, Zustand |
| Responsive Design | Mobile-first approach essential |

### Backend

| Component | Technology Options |
|-----------|-------------------|
| Server | Node.js/Express, Python/Django, or Go |
| Database | PostgreSQL (articles, users), Redis (caching) |
| API | REST or GraphQL |
| Authentication | OAuth, JWT tokens |

### News Aggregation Engine

| Function | Implementation |
|----------|---------------|
| RSS Feed Parsing | Python (feedparser) or Node.js libraries |
| Web Scraping | Scrapy, Puppeteer, or Playwright (with legal considerations) |
| Article Matching | NLP to match articles covering the same story |
| Bias Classification | ML model trained on political leaning indicators |
| Summarisation | LLM API (OpenAI, Anthropic) or open-source models |

### Infrastructure
- **Hosting**: AWS, GCP, or Vercel
- **CDN**: Cloudflare for global performance
- **Search**: Elasticsearch or Algolia
- **Scheduling**: Cron jobs or message queues for regular scraping

### Key Technical Challenges

1. **Article Matching** - Determining which articles from different sources cover the same story requires sophisticated NLP (entity recognition, topic modelling)

2. **Bias Classification** - Building or sourcing a reliable model to categorise political leaning of sources/articles

3. **Copyright & Legal** - You'll need to summarise/excerpt rather than reproduce full articles; consider licensing agreements

4. **Real-time Updates** - International news moves fast; need efficient polling/webhook systems

5. **Scale** - Processing hundreds of articles daily from dozens of sources

### Estimated Skill Requirements

- **Frontend Developer** - UI/UX, responsive design
- **Backend Developer** - API design, database architecture
- **ML/NLP Engineer** - Article matching, bias detection, summarisation
- **DevOps** - Infrastructure, CI/CD, monitoring
- **Editorial/Content** - Source curation, quality control, bias calibration

---

## Part 3: Backend Architecture (Detailed)

### Server Layer

The server handles all requests between your frontend and data sources.

**Core Responsibilities:**
- Serve API endpoints for the frontend to fetch articles, comparisons, topics
- Handle user authentication and preferences
- Manage rate limiting and caching
- Orchestrate the news aggregation pipeline

**Typical API Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /stories` | Fetch matched story clusters with left/right articles |
| `GET /stories/:id` | Single story with full comparison analysis |
| `GET /sources` | List of all news sources with bias ratings |
| `GET /topics/:topic` | Articles filtered by category (trade, geopolitics, etc.) |
| `POST /users/preferences` | Save user's source/topic preferences |
| `GET /briefings/daily` | Curated daily digest |

**Technology Choice Considerations:**
- **Node.js/Express** - Good if your team knows JavaScript; large ecosystem
- **Python/Django or FastAPI** - Better if leaning heavily on ML/NLP (Python dominates that space)
- **Go** - High performance for processing large volumes of articles

### Database Design

**Primary Database (PostgreSQL)**

```
┌─────────────────────────────────────────────────────────────┐
│ sources                                                      │
├─────────────────────────────────────────────────────────────┤
│ id, name, url, rss_feed_url, bias_rating (-10 to +10),      │
│ country, language, credibility_score, active                 │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ articles                                                     │
├─────────────────────────────────────────────────────────────┤
│ id, source_id, title, url, published_at, scraped_at,        │
│ full_text, summary, topics[], entities[], embedding_vector   │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ story_clusters                                               │
├─────────────────────────────────────────────────────────────┤
│ id, canonical_title, summary, created_at, topics[],         │
│ left_article_ids[], centre_article_ids[], right_article_ids[]│
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ comparisons                                                  │
├─────────────────────────────────────────────────────────────┤
│ id, story_cluster_id, left_framing, right_framing,          │
│ agreements[], disagreements[], blind_spots[], generated_at   │
└─────────────────────────────────────────────────────────────┘
```

**Cache Layer (Redis)**
- Store frequently accessed stories (hot news)
- Cache expensive NLP results
- Session management
- Rate limiting counters

**Vector Database (Pinecone, Weaviate, or pgvector)**
- Store article embeddings for semantic similarity matching
- Essential for finding articles about the same story

### Background Job System

News aggregation can't happen on-demand—it needs scheduled background processing.

**Job Queue (Bull, Celery, or similar)**

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  Scheduler     │────▶│  Job Queue     │────▶│  Workers       │
│  (every 15min) │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘
                                                     │
                              ┌───────────────────────┼───────────────────────┐
                              ▼                       ▼                       ▼
                       ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
                       │ Fetch RSS   │        │ Match       │        │ Generate    │
                       │ & Scrape    │        │ Stories     │        │ Comparisons │
                       └─────────────┘        └─────────────┘        └─────────────┘
```

---

## Part 4: News Aggregation Engine (Detailed)

### Stage 1: Article Collection

**RSS Feed Parsing**

Most news sites publish RSS feeds—structured XML with headlines, summaries, and links.

```
Your System                          News Sources
     │                                    │
     │──── Request RSS Feed ─────────────▶│ (The Guardian)
     │◀─── XML with 20-50 recent items ───│
     │                                    │
     │──── Request RSS Feed ─────────────▶│ (Wall Street Journal)
     │◀─── XML with 20-50 recent items ───│
     │                                    │
     ▼
┌─────────────────────────────────────────┐
│ Parse XML, extract:                     │
│ - Title                                 │
│ - URL                                   │
│ - Published timestamp                   │
│ - Summary/description                   │
└─────────────────────────────────────────┘
```

**Web Scraping (for full article text)**

RSS feeds usually only give summaries. To get full text:

1. Follow the article URL
2. Parse the HTML
3. Extract the main content (ignoring ads, navigation, etc.)
4. Clean and normalise the text

**Legal Considerations:**
- Many sites prohibit scraping in their Terms of Service
- Consider: licensing deals, using only excerpts/summaries, or APIs where available
- Some aggregators (like Google News) have special agreements

### Stage 2: Article Processing

Once you have raw articles, you need to extract structured information.

**Entity Extraction**

Identify key entities mentioned in each article:
- **People**: Xi Jinping, Ursula von der Leyen, Jerome Powell
- **Organisations**: NATO, IMF, OPEC, European Commission
- **Locations**: Taiwan Strait, Suez Canal, City of London
- **Events**: G7 Summit, COP30, Federal Reserve meeting

**Topic Classification**

Assign articles to your categories:
- Trade & Tariffs
- Geopolitics & Diplomacy
- Investment & Capital Flows
- etc.

This can be done with:
- Keyword matching (simple but limited)
- Traditional ML classifiers (trained on labelled examples)
- LLM-based classification (more flexible, higher cost)

**Embedding Generation**

Convert each article into a numerical vector that captures its semantic meaning.

```
Article: "EU imposes new tariffs on Chinese electric vehicles..."
                    │
                    ▼
         ┌─────────────────┐
         │ Embedding Model │
         │ (e.g., OpenAI)  │
         └─────────────────┘
                    │
                    ▼
         [0.023, -0.156, 0.892, ..., 0.445]  (1536 dimensions)
```

Articles about similar topics will have similar vectors, enabling matching.

### Stage 3: Story Matching

**The Core Challenge:**
You have 500 articles from 50 sources. How do you know which ones are about the same story?

**Approach: Clustering by Similarity**

```
┌─────────────────────────────────────────────────────────────────┐
│                     All Articles (24hr window)                  │
│                                                                 │
│   [A1] [A2] [A3] [A4] [A5] [A6] [A7] [A8] [A9] [A10] ...       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Compute pairwise similarity  │
              │  using embedding vectors      │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Cluster articles with        │
              │  similarity > threshold       │
              └───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Story Clusters                                                 │
│                                                                 │
│  Cluster 1: [A1, A4, A7]     "EU-China EV tariff dispute"      │
│  Cluster 2: [A2, A5, A9]     "Fed interest rate decision"       │
│  Cluster 3: [A3, A6]         "Taiwan Strait military activity"  │
│  Cluster 4: [A8]             (singleton - no matches)           │
└─────────────────────────────────────────────────────────────────┘
```

**Matching Signals (combined for accuracy):**
- Embedding similarity (semantic closeness)
- Entity overlap (same people/places mentioned)
- Temporal proximity (published within hours of each other)
- Topic alignment (same category)

### Stage 4: Comparison Generation

Once you have a cluster of articles about the same story, generate the comparison.

**Input to LLM:**

```
You are analysing coverage of the same international affairs story 
from different political perspectives.

LEFT-LEANING SOURCES:
- The Guardian: [article summary]
- Al Jazeera: [article summary]

RIGHT-LEANING SOURCES:
- Wall Street Journal: [article summary]
- The Telegraph: [article summary]

Generate:
1. A neutral factual summary of the story
2. How left-leaning sources frame the issue
3. How right-leaning sources frame the issue
4. Key points of agreement
5. Key points of disagreement
6. What each side tends to emphasise or omit
```

**Output Structure:**

```json
{
  "neutral_summary": "The EU announced 38% tariffs on Chinese EVs...",
  "left_framing": "Emphasises environmental hypocrisy, worker exploitation concerns...",
  "right_framing": "Focuses on national security, unfair state subsidies...",
  "agreements": ["Both acknowledge China's EV dominance", "Both note EU division"],
  "disagreements": ["Whether tariffs help or hurt climate goals"],
  "left_blind_spots": ["Less coverage of security implications"],
  "right_blind_spots": ["Less coverage of consumer price impact"]
}
```

### Pipeline Summary

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  FETCH  │───▶│ PROCESS │───▶│  MATCH  │───▶│ COMPARE │───▶│  STORE  │
│         │    │         │    │         │    │         │    │         │
│ RSS     │    │ Extract │    │ Cluster │    │ Generate│    │ Database│
│ Scrape  │    │ entities│    │ similar │    │ LLM     │    │ Cache   │
│         │    │ Embed   │    │ articles│    │ analysis│    │ Index   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┘
                              │
                    Runs every 15-60 minutes
```

---

## Part 5: Cost Estimates

| Component | Cost Driver | Estimate (monthly) |
|-----------|-------------|-------------------|
| LLM API (embeddings) | Per article processed | £50-200 |
| LLM API (comparisons) | Per story cluster | £100-500 |
| Vector database | Storage + queries | £50-150 |
| Server hosting | Compute for pipeline | £100-300 |
| PostgreSQL | Storage | £20-50 |

Costs scale with volume—processing 1,000 articles/day is very different from 10,000.

---

## Part 6: Additional Feature Ideas

### Content & Editorial Features

#### 1. "Timeline of a Story"
Track how a story evolves over days/weeks—showing how left and right narratives shift as new information emerges. Particularly valuable for ongoing situations like trade negotiations or conflicts.

#### 2. "Fact vs. Opinion Separator"
Use NLP to highlight which statements in articles are factual claims vs. editorial opinion. Colour-code them so readers can distinguish between the two.

#### 3. "The Consensus Zone"
A dedicated section for stories where left and right sources largely agree. This is newsworthy in itself—when The Guardian and The Telegraph align on something, that's significant.

#### 4. "Source of the Claim"
For major assertions, trace back where the claim originated. Did 15 outlets all cite the same anonymous source? Did the framing start from a think tank or government press release?

#### 5. Historical Context Cards
For recurring topics (US-China relations, Brexit effects, etc.), provide evergreen context cards that explain the background without readers needing to search elsewhere.

### Trust & Transparency Features

#### 6. "Show Your Working"
Display exactly how you classified each source's political leaning. Let users see (and challenge) the methodology. Transparency builds trust.

#### 7. Bias Rating Crowdsourcing
Let verified readers vote on whether they agree with your bias classifications. Over time, this creates a community-validated rating system.

#### 8. Funding & Ownership Database
For each source, show who owns it, major funders, and any notable editorial interventions. Readers increasingly want this context.

#### 9. Correction Tracker
Track when outlets issue corrections on international affairs stories. Which sources correct more? Which rarely do?

### User Engagement & Personalisation

#### 10. "Challenge Your Bubble"
A feature that deliberately shows users perspectives they typically avoid. If someone reads mostly left-leaning analysis, prompt them with right-leaning takes they might find compelling.

#### 11. Prediction Markets Integration
For ongoing situations (Will the trade deal pass? Will sanctions be lifted?), show aggregated prediction market odds. Compare with what left/right commentators are predicting.

#### 12. "Steelman" Feature
For each perspective, generate the strongest possible version of the argument—even if the original article didn't articulate it well. Helps readers understand the best case for each side.

#### 13. Reading History Insights
Show users their own consumption patterns: "This month you read 73% left-leaning sources on trade issues." Non-judgmental, just informative.

### Community & Expert Features

#### 14. Expert Commentary Layer
Partner with academics, former diplomats, and analysts to provide brief expert annotations on major stories. Not opinion—just "here's what this means technically."

#### 15. Regional Correspondent Network
International affairs look different from different countries. A US-China trade story reads differently in Brussels, Beijing, and Brasília. Show regional perspectives, not just left/right.

#### 16. "Ask the Other Side"
Moderated Q&A where readers can pose genuine questions to people holding opposing views. Structured dialogue rather than comment section chaos.

### Data & Research Tools

#### 17. Sentiment Tracking Dashboard
Track how positive/negative coverage is toward specific countries, leaders, or institutions over time. Visualise shifts in media sentiment.

```
Coverage Sentiment: China
─────────────────────────────────────
Left sources:   ████████░░ -2.3 (negative)
Right sources:  ██████████ -4.1 (very negative)
                ─────────────────────────
                Jan    Mar    May    Jul
```

#### 18. "Coverage Gap" Alerts
Identify stories getting heavy coverage in non-English or regional media but being ignored by major English-language outlets. What are we missing?

#### 19. API for Researchers
Academics studying media bias would pay for access to your structured data. Secondary revenue stream and builds credibility.

#### 20. Downloadable Datasets
Monthly dumps of your classified articles for academic research. Builds goodwill and citations.

### Distribution & Reach

#### 21. Daily Audio Briefing
5-10 minute podcast summarising the day's key stories with left/right framing. Easy to produce with text-to-speech (or human narration for premium feel).

#### 22. WhatsApp/Telegram Newsletter
In many regions, messaging apps are primary news distribution. Short daily digest optimised for chat.

#### 23. Browser Extension
Highlight political leaning when users visit news sites directly. "You're reading The Telegraph (centre-right). See how The Guardian covered this story →"

#### 24. Embeddable Widgets
Let other sites embed your "left vs right" comparison boxes. Spreads brand awareness and drives traffic.

---

## Part 7: Monetisation Strategies

| Model | Description |
|-------|-------------|
| **Freemium** | Basic comparisons free; deep analysis, historical data, alerts behind paywall |
| **Institutional** | Universities, newsrooms, think tanks pay for API/bulk access |
| **Newsletter sponsorship** | Non-intrusive sponsors for daily briefings |
| **Events** | Webinars/panels on major international affairs topics |
| **White-label** | License your engine to news organisations wanting to show "other perspectives" |

**Avoid:** Advertising from politically-aligned organisations (undermines trust).

---

## Part 8: Potential Partnerships

- **Fact-checking organisations** (Full Fact, PolitiFact) for credibility
- **Universities** with international relations departments for expert input
- **News literacy nonprofits** for educational content
- **Existing aggregators** (Feedly, Flipboard) for distribution
- **Think tanks** (Chatham House, Brookings, CSIS) as sources and promoters

---

## Part 9: Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Accusations of bias in your own classifications | Transparent methodology, external audits, crowdsourced validation |
| Legal challenges from publishers | Use excerpts/summaries, pursue licensing where possible |
| Filter bubble reinforcement | "Challenge your bubble" features, balanced defaults |
| Information overload | Strong curation, clear hierarchy, progressive disclosure |
| Platform capture (social media algorithm changes) | Own your audience via email/RSS, diversify distribution |

---

## Part 10: Unique Differentiator Opportunity

### "The International View"

Most "left vs right" framing is Anglo-American. But on international affairs, the more interesting divide is often **domestic vs. foreign** perspective:

- How do Chinese state media cover the same trade story?
- What does Le Monde say that neither The Guardian nor WSJ mention?
- How does Al Jazeera frame a Middle East story differently from all Western outlets?

This makes your site genuinely unique rather than another US culture-war lens applied to world news.

---

## Next Steps

1. **Validate the concept** - Survey potential users about which features matter most
2. **Define MVP scope** - Pick 2-3 core features for initial launch
3. **Source audit** - Create initial list of 20-30 sources with bias ratings
4. **Technical prototype** - Build basic RSS ingestion and clustering pipeline
5. **Legal review** - Understand copyright implications for your jurisdiction
6. **Funding/resourcing** - Determine budget and team requirements

---

*Document created: May 2026*
