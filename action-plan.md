# International Affairs News Platform - Action Plan

A detailed execution plan for building and launching the news comparison platform.

---

## Phase 0: Foundation & Validation (Pre-Build)

### 0.1 Market Research & Validation

**Objective:** Confirm there's genuine demand before investing in development.

| Task | Actions | Outputs |
|------|---------|---------|
| Competitor analysis | Research existing platforms (AllSides, Ground News, Biasly, The Flip Side). Document their strengths, weaknesses, pricing, and gaps | Competitor matrix spreadsheet |
| User interviews | Speak to 15-20 potential users (journalists, policy analysts, academics, engaged citizens). Ask about current pain points | Interview notes, key insights document |
| Survey | Create online survey about news consumption habits and interest in the concept. Target 200+ responses | Survey results analysis |
| Validate willingness to pay | Include pricing questions in survey. Test different price points | Pricing sensitivity data |

**Key Questions to Answer:**
- Who exactly is the target user? (General public vs. professionals vs. academics)
- What's the primary use case? (Daily briefing vs. deep research vs. media literacy)
- Is this a "nice to have" or a "must have" for users?
- What would make someone pay for this vs. using free alternatives?

**Decision Gate:** Only proceed if research indicates strong demand and a clear gap in the market.

---

### 0.2 Define MVP Scope

**Objective:** Identify the minimum feature set for initial launch.

**Recommended MVP Features:**
1. ✅ Article aggregation from 20-30 curated sources
2. ✅ Automated story clustering (matching articles on same topic)
3. ✅ Left/Right comparison view with AI-generated summaries
4. ✅ Basic topic filtering (5-6 categories)
5. ✅ Email newsletter (daily digest)
6. ✅ Simple responsive website

**Explicitly NOT in MVP:**
- ❌ User accounts and personalisation
- ❌ Comments and community features
- ❌ Browser extension
- ❌ Podcast/audio
- ❌ API access
- ❌ Mobile apps

**Deliverable:** MVP specification document (2-3 pages)

---

### 0.3 Legal & Compliance Review

**Objective:** Understand legal constraints before building.

| Task | Details |
|------|---------|
| Copyright research | Consult with media lawyer on fair use/fair dealing for news aggregation in your jurisdiction (UK/EU/US differ significantly) |
| Terms of service audit | Review ToS of target news sources for scraping restrictions |
| Licensing options | Research news licensing schemes (e.g., NLA in UK) and costs |
| GDPR/privacy | If collecting user data, ensure compliance framework |
| Company structure | Decide on legal entity (Ltd, LLC, etc.) |

**Key Legal Questions:**
- Can you display headlines and excerpts without licensing?
- What's the maximum excerpt length considered fair use?
- Do you need to link back to original articles?
- What happens if a publisher sends a takedown notice?

**Deliverable:** Legal risk assessment and recommended approach

---

### 0.4 Source Curation & Bias Methodology

**Objective:** Build the foundation of credible source ratings.

**Source Selection Criteria:**
- Covers international affairs regularly
- Has RSS feed or reliable structure for scraping
- Established publication (not fly-by-night)
- Clear editorial perspective (easier to classify)
- English language (for MVP)

**Initial Source List (Target: 30 sources)**

| Category | Left-Leaning | Centre | Right-Leaning |
|----------|--------------|--------|---------------|
| UK | The Guardian, The Independent, The Mirror | BBC, Reuters UK, Financial Times | The Telegraph, The Spectator, Daily Mail |
| US | New York Times, Washington Post, The Atlantic, Vox | AP, Reuters, NPR | Wall Street Journal, Fox News, National Review, The Dispatch |
| International | Al Jazeera, Der Spiegel (English) | France 24, DW | - |

**Bias Classification Methodology:**

1. **Research existing ratings** - Cross-reference AllSides, Ad Fontes Media, MBFC
2. **Document your methodology** - Criteria used (editorial stance, ownership, story selection, language patterns)
3. **Create rating scale** - e.g., -5 (far left) to +5 (far right), with 0 as centre
4. **Peer review** - Have 3-5 people independently rate sources, compare results
5. **Publish methodology** - Transparency is critical for credibility

**Deliverable:** Source database with ratings and methodology document

---

## Phase 1: Technical Foundation

### 1.1 Infrastructure Setup

**Objective:** Establish development and production environments.

| Task | Tool/Service | Notes |
|------|--------------|-------|
| Version control | GitHub/GitLab | Private repo, branch protection |
| Cloud provider | AWS / GCP / DigitalOcean | Start small, scale later |
| Database | PostgreSQL (managed service) | Supabase, AWS RDS, or Railway |
| Cache | Redis (managed) | Upstash or AWS ElastiCache |
| Vector database | Pinecone / Weaviate / pgvector | For article embeddings |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Monitoring | Sentry + basic cloud monitoring | Error tracking from day one |
| Domain & DNS | Cloudflare | Also provides CDN and DDoS protection |

**Environment Structure:**
- `development` - Local development
- `staging` - Testing before production
- `production` - Live site

**Deliverable:** Infrastructure documentation, all services provisioned

---

### 1.2 Backend Development

**Objective:** Build the core API and data layer.

**Technology Recommendation:** Python (FastAPI) - Best ecosystem for NLP/ML work

**Database Schema Implementation:**

```sql
-- Core tables to implement

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    rss_feed_url VARCHAR(500),
    bias_rating DECIMAL(3,1),  -- -5.0 to +5.0
    bias_category VARCHAR(20),  -- 'left', 'centre-left', 'centre', 'centre-right', 'right'
    country VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    credibility_score DECIMAL(3,1),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    external_id VARCHAR(500),  -- URL or unique ID from source
    title TEXT NOT NULL,
    url VARCHAR(1000) NOT NULL,
    summary TEXT,
    full_text TEXT,
    published_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT NOW(),
    topics VARCHAR(100)[],
    entities JSONB,
    embedding VECTOR(1536),  -- If using pgvector
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(url)
);

CREATE TABLE story_clusters (
    id SERIAL PRIMARY KEY,
    canonical_title TEXT,
    neutral_summary TEXT,
    topics VARCHAR(100)[],
    primary_entities JSONB,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cluster_articles (
    cluster_id INTEGER REFERENCES story_clusters(id),
    article_id INTEGER REFERENCES articles(id),
    similarity_score DECIMAL(4,3),
    PRIMARY KEY (cluster_id, article_id)
);

CREATE TABLE comparisons (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER REFERENCES story_clusters(id) UNIQUE,
    neutral_summary TEXT,
    left_framing TEXT,
    right_framing TEXT,
    agreements TEXT[],
    disagreements TEXT[],
    left_blind_spots TEXT[],
    right_blind_spots TEXT[],
    generated_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**API Endpoints to Build:**

| Priority | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| P0 | `/api/stories` | GET | List story clusters with comparisons |
| P0 | `/api/stories/{id}` | GET | Single story with full details |
| P0 | `/api/topics` | GET | List available topics |
| P0 | `/api/stories?topic={topic}` | GET | Filter stories by topic |
| P1 | `/api/sources` | GET | List all sources with ratings |
| P1 | `/api/briefing/daily` | GET | Today's digest |
| P2 | `/api/newsletter/subscribe` | POST | Email signup |

**Deliverable:** Working API with all P0 endpoints, deployed to staging

---

### 1.3 News Aggregation Pipeline

**Objective:** Build the automated system that fetches, processes, and matches articles.

**Pipeline Architecture:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGGREGATION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐                                                       │
│  │   SCHEDULER  │  Triggers every 30 minutes                           │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     JOB 1: FETCH ARTICLES                         │  │
│  │                                                                    │  │
│  │  For each active source:                                          │  │
│  │    1. Fetch RSS feed                                              │  │
│  │    2. Parse items (title, URL, published date, summary)           │  │
│  │    3. Check if article already exists (by URL)                    │  │
│  │    4. If new: fetch full article text (scrape or API)             │  │
│  │    5. Store in articles table                                     │  │
│  │                                                                    │  │
│  │  Error handling: Log failures, don't block other sources          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    JOB 2: PROCESS ARTICLES                        │  │
│  │                                                                    │  │
│  │  For each unprocessed article:                                    │  │
│  │    1. Clean text (remove HTML, normalize whitespace)              │  │
│  │    2. Extract entities (NER: people, orgs, places)                │  │
│  │    3. Classify topics (trade, geopolitics, etc.)                  │  │
│  │    4. Generate embedding (OpenAI text-embedding-3-small)          │  │
│  │    5. Update article record                                       │  │
│  │                                                                    │  │
│  │  Batch processing: 50 articles per batch for API efficiency       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    JOB 3: CLUSTER STORIES                         │  │
│  │                                                                    │  │
│  │  Time window: Last 48 hours of articles                           │  │
│  │                                                                    │  │
│  │  Algorithm:                                                       │  │
│  │    1. Get all unclustered articles from window                    │  │
│  │    2. For each article, find similar articles:                    │  │
│  │       - Vector similarity > 0.85 threshold                        │  │
│  │       - Entity overlap > 50%                                      │  │
│  │       - Same primary topic                                        │  │
│  │    3. Group into clusters using agglomerative clustering          │  │
│  │    4. For each cluster:                                           │  │
│  │       - Generate canonical title                                  │  │
│  │       - Identify left/centre/right articles                       │  │
│  │    5. Create/update story_clusters records                        │  │
│  │                                                                    │  │
│  │  Only create cluster if: >= 2 articles from different sources     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  JOB 4: GENERATE COMPARISONS                      │  │
│  │                                                                    │  │
│  │  For each cluster without comparison:                             │  │
│  │    1. Gather all article summaries/excerpts                       │  │
│  │    2. Group by political leaning                                  │  │
│  │    3. Call LLM with comparison prompt                             │  │
│  │    4. Parse structured response                                   │  │
│  │    5. Store in comparisons table                                  │  │
│  │                                                                    │  │
│  │  Only generate if: cluster has both left AND right sources        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**LLM Prompt for Comparisons:**

```
You are an expert analyst comparing news coverage of international affairs 
from different political perspectives. Analyse the following articles about 
the same story.

STORY TOPIC: {cluster_canonical_title}

LEFT-LEANING SOURCES:
{for each left article}
- {source_name}: {article_summary_or_excerpt}
{end for}

CENTRE SOURCES:
{for each centre article}
- {source_name}: {article_summary_or_excerpt}
{end for}

RIGHT-LEANING SOURCES:
{for each right article}
- {source_name}: {article_summary_or_excerpt}
{end for}

Provide your analysis in the following JSON format:
{
  "neutral_summary": "A 2-3 sentence factual summary of what happened",
  "left_framing": "How left-leaning sources frame this story (2-3 sentences)",
  "right_framing": "How right-leaning sources frame this story (2-3 sentences)",
  "agreements": ["Point both sides agree on", "Another point of agreement"],
  "disagreements": ["Key point of disagreement", "Another disagreement"],
  "left_blind_spots": ["What left sources underemphasise or ignore"],
  "right_blind_spots": ["What right sources underemphasise or ignore"]
}

Be balanced and fair. Represent each perspective accurately without editorialising.
```

**Deliverable:** Working pipeline processing articles end-to-end

---

### 1.4 Frontend Development

**Objective:** Build the user-facing website.

**Technology Recommendation:** Next.js (React) with Tailwind CSS

**Page Structure:**

```
/                       # Homepage - Today's top stories
/story/{id}             # Individual story comparison view
/topic/{topic}          # Stories filtered by topic
/sources                # Source directory with ratings
/about                  # About page, methodology
/newsletter             # Newsletter signup
```

**Homepage Wireframe:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [LOGO]              Trade | Geopolitics | Economy | ...    [Subscribe] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TODAY'S TOP STORIES                                         May 22     │
│  ═══════════════════                                                    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  EU-China EV Tariff Dispute Escalates                              │ │
│  │  ──────────────────────────────────────────                        │ │
│  │                                                                     │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │ │
│  │  │ LEFT            │  │ CENTRE          │  │ RIGHT           │     │ │
│  │  │ ───────         │  │ ────────        │  │ ──────          │     │ │
│  │  │ Guardian says...│  │ The EU has...   │  │ WSJ reports...  │     │ │
│  │  │                 │  │                 │  │                 │     │ │
│  │  │ [2 sources]     │  │ [1 source]      │  │ [2 sources]     │     │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘     │ │
│  │                                                                     │ │
│  │  Agreements: Both sides note...    Disagreements: Left says X...   │ │
│  │                                                        [Read more →]│ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Fed Signals Rate Cuts May Be Delayed                              │ │
│  │  ...                                                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Taiwan Strait Tensions Rise After Military Exercise               │ │
│  │  ...                                                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Individual Story Page:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [← Back]                                                               │
│                                                                         │
│  EU-China EV Tariff Dispute Escalates                                  │
│  ══════════════════════════════════════                                │
│  Trade & Tariffs  •  Updated 2 hours ago  •  5 sources                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  THE STORY                                                              │
│  ─────────                                                              │
│  The European Commission announced provisional tariffs of up to 38%    │
│  on Chinese-made electric vehicles, citing unfair state subsidies.     │
│  China has warned of retaliatory measures...                           │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────┐     ┌───────────────────────────┐       │
│  │  LEFT PERSPECTIVE         │     │  RIGHT PERSPECTIVE        │       │
│  │  ─────────────────        │     │  ──────────────────       │       │
│  │                           │     │                           │       │
│  │  Left-leaning sources     │     │  Right-leaning sources    │       │
│  │  emphasise the climate    │     │  focus on national        │       │
│  │  implications and         │     │  security concerns and    │       │
│  │  potential impact on      │     │  unfair Chinese state     │       │
│  │  consumers...             │     │  subsidies...             │       │
│  │                           │     │                           │       │
│  │  Sources:                 │     │  Sources:                 │       │
│  │  • The Guardian           │     │  • Wall Street Journal    │       │
│  │  • Al Jazeera             │     │  • The Telegraph          │       │
│  └───────────────────────────┘     └───────────────────────────┘       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  THEY AGREE ON                       THEY DISAGREE ON                  │
│  ──────────────                      ───────────────                   │
│  ✓ China dominates EV market         ✗ Whether tariffs help climate   │
│  ✓ EU is divided on approach         ✗ Impact on EU auto industry     │
│  ✓ Retaliation is likely             ✗ Role of protectionism          │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ALL SOURCES                                                            │
│  ───────────                                                            │
│                                                                         │
│  [Guardian logo]  The Guardian                              LEFT       │
│  "EU's tariffs on Chinese EVs risk climate goals"                      │
│  Published 3 hours ago                                    [Read →]     │
│                                                                         │
│  [WSJ logo]  Wall Street Journal                           RIGHT       │
│  "EU Takes Hard Line on Chinese EV Subsidies"                          │
│  Published 4 hours ago                                    [Read →]     │
│                                                                         │
│  ...                                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Design Principles:**
- Clean, minimal, trust-building aesthetic
- Clear visual distinction between left/centre/right
- Mobile-first responsive design
- Fast loading (< 2s)
- Accessible (WCAG 2.1 AA)

**Deliverable:** Functional website deployed to staging

---

## Phase 2: Testing & Refinement

### 2.1 Internal Testing

**Duration:** 2 weeks

| Test Type | Focus Areas |
|-----------|-------------|
| Functional testing | All user flows work correctly |
| Pipeline reliability | Articles processing without errors for 7+ days |
| Comparison quality | LLM outputs are accurate and balanced |
| Performance | Page load times, API response times |
| Mobile testing | All pages work on iOS and Android |
| Edge cases | Empty states, errors, missing data |

**Quality Checklist for Comparisons:**
- [ ] Neutral summary is factually accurate
- [ ] Left framing fairly represents left sources
- [ ] Right framing fairly represents right sources
- [ ] Agreements are genuine points of consensus
- [ ] Disagreements capture real differences
- [ ] No editorialising or bias in the analysis itself

---

### 2.2 Beta Testing

**Duration:** 4 weeks

**Beta User Recruitment:**
- Target: 50-100 users
- Mix of: journalists, policy wonks, academics, engaged citizens
- Diversity of political perspectives (critical for credibility)

**Feedback Collection:**
- In-app feedback widget
- Weekly survey
- 5-10 user interviews

**Key Metrics to Track:**
- Daily/weekly active users
- Stories viewed per session
- Newsletter signup rate
- Time on site
- Return visit rate
- Qualitative feedback on bias/accuracy

**Iterate Based on Feedback:**
- Prioritise fixes and improvements
- Adjust comparison prompts if needed
- Refine source ratings if challenged
- Fix UX issues

---

## Phase 3: Launch

### 3.1 Pre-Launch Checklist

**Technical:**
- [ ] All critical bugs fixed
- [ ] Performance optimised
- [ ] Error monitoring active
- [ ] Backup systems in place
- [ ] SSL certificate active
- [ ] Security audit complete

**Content:**
- [ ] About page complete with methodology
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Source directory complete
- [ ] At least 7 days of stories in archive

**Marketing:**
- [ ] Landing page optimised
- [ ] Social media accounts created
- [ ] Press release drafted
- [ ] Outreach list prepared
- [ ] Newsletter signup working

---

### 3.2 Launch Strategy

**Soft Launch (Week 1):**
- Announce to beta users
- Fix any immediate issues
- Build initial content archive

**Public Launch (Week 2):**

| Channel | Action |
|---------|--------|
| Press | Send press release to media/tech journalists |
| Social | Launch posts on Twitter/X, LinkedIn |
| Reddit | Posts in relevant subreddits (r/geopolitics, r/neutralnews, r/media_criticism) |
| Newsletters | Pitch to media/tech newsletter curators |
| Podcasts | Pitch interviews on media/politics podcasts |
| Academic | Reach out to journalism schools, IR departments |

**Launch Day Priorities:**
- Monitor site performance
- Respond to feedback quickly
- Fix critical issues immediately
- Engage with social media comments
- Track sign-ups and usage

---

## Phase 4: Post-Launch Growth

### 4.1 First 90 Days

**Week 1-4: Stabilise**
- Fix bugs and issues
- Respond to user feedback
- Refine comparison quality
- Optimise performance

**Week 5-8: Iterate**
- A/B test homepage layouts
- Improve story matching accuracy
- Add more sources based on user requests
- Enhance mobile experience

**Week 9-12: Grow**
- Launch email newsletter properly
- Begin content marketing (blog posts about media bias)
- Partnership outreach
- Consider paid promotion (limited)

### 4.2 Key Performance Indicators

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Monthly active users | 1,000 | 5,000 |
| Newsletter subscribers | 500 | 2,000 |
| Stories generated/day | 15+ | 25+ |
| Average session duration | > 3 min | > 4 min |
| Return visitor rate | > 20% | > 30% |

### 4.3 Feature Roadmap (Post-MVP)

**Quarter 2:**
- User accounts and preferences
- "Challenge your bubble" feature
- Topic alerts (email when story matches interest)
- Improved search

**Quarter 3:**
- Daily audio briefing (podcast)
- Browser extension
- Historical archive and search
- API for researchers (beta)

**Quarter 4:**
- Mobile app (React Native)
- Premium tier launch
- Sentiment tracking dashboard
- Institutional sales outreach

---

## Resource Requirements

### Team (Minimum Viable)

| Role | Responsibility | Commitment |
|------|----------------|------------|
| Technical Lead / Full-stack Developer | Backend, frontend, infrastructure | Full-time |
| ML/NLP Engineer | Article processing, matching, embeddings | Part-time → Full-time |
| Product / Editorial Lead | Source curation, quality control, content | Part-time → Full-time |
| Designer | UI/UX, brand, marketing materials | Contract/Part-time |

**Alternative: Solo Founder Route**
If building alone, you'll need strong full-stack and ML skills, and should expect a longer timeline.

### Budget Estimate (First 6 Months)

| Category | Monthly | 6-Month Total |
|----------|---------|---------------|
| Cloud infrastructure | £200-400 | £1,500-2,500 |
| LLM API costs (OpenAI/Anthropic) | £300-600 | £2,000-4,000 |
| Vector database | £50-100 | £300-600 |
| Domain, DNS, email | £20 | £120 |
| Design/branding (contract) | - | £2,000-5,000 |
| Legal (company setup, ToS) | - | £1,000-2,000 |
| Marketing/PR | £100-300 | £1,000-2,000 |
| **TOTAL (excluding salaries)** | | **£8,000-16,000** |

Salaries/contractor fees would be additional and depend heavily on location and experience levels.

---

## Timeline Summary

| Phase | Duration | Key Milestone |
|-------|----------|---------------|
| Phase 0: Foundation | 4-6 weeks | Validated concept, legal clarity, source list |
| Phase 1: Build | 8-12 weeks | Working MVP on staging |
| Phase 2: Test | 4-6 weeks | Beta tested, refined |
| Phase 3: Launch | 2 weeks | Public launch |
| Phase 4: Grow | Ongoing | 5,000 MAU by month 3 |

**Total time to launch: 4-6 months** (depending on team size and commitment)

---

## Risk Mitigation Plan

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Legal challenge from publisher | Medium | High | Use excerpts only, have takedown process, build relationships |
| LLM generates biased comparisons | Medium | High | Human review sample, user feedback, prompt refinement |
| Low user adoption | Medium | High | Validate before building, focus on SEO and newsletter |
| Source ratings disputed | High | Medium | Transparent methodology, allow user feedback, cite external ratings |
| Technical scaling issues | Low | Medium | Start with managed services, monitor closely |
| Competitor launches similar product | Medium | Medium | Move fast, differentiate on quality and trust |
| Funding runs out | Medium | High | Keep costs low, consider grants, plan for monetisation early |

---

## Decision Points / Go/No-Go Gates

**Gate 1 (End of Phase 0):** Does market research support proceeding?
- If no clear demand or insurmountable legal barriers → Pivot or stop

**Gate 2 (Mid Phase 1):** Is the technical approach working?
- If article matching is too unreliable → Simplify to manual curation

**Gate 3 (End of Phase 2):** Is beta feedback positive?
- If users don't find value → Major pivot or stop

**Gate 4 (Month 2 post-launch):** Are growth metrics on track?
- If not → Reassess strategy, product-market fit

---

## Next Immediate Actions

1. **This week:** Begin competitor analysis (AllSides, Ground News, The Flip Side)
2. **This week:** Draft user interview questions
3. **Next week:** Conduct 5 initial user interviews
4. **Next week:** Research media lawyer in your jurisdiction
5. **Week 3:** Create initial source list and bias ratings
6. **Week 3:** Make go/no-go decision on proceeding to build

---

*Action plan created: May 2026*
