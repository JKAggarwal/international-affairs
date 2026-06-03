// Use the local API during development, and the deployed API in production.
// Override at any time by setting window.API_BASE before this script loads.
const API_BASE = (function () {
    if (window.API_BASE) return window.API_BASE;
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1' || host === '') {
        return 'http://localhost:8000/api';
    }
    // Netlify preview URL before custom api.* DNS is live
    if (host.endsWith('.netlify.app')) {
        return 'https://international-affairs-api.onrender.com/api';
    }
    return 'https://api.internationalaffairs.org.uk/api';
})();
const REFRESH_INTERVAL_MS = 30 * 60 * 1000; // backend fetches every 6h; poll lightly to pick up new data
let currentTopic = 'all';
let inSearchMode = false;

document.addEventListener('DOMContentLoaded', function () {
    const storiesContainer = document.querySelector('.stories .container');
    if (storiesContainer) {
        loadBriefing();
        loadGroupedStories();
        startAutoRefresh();
    }

    const storyPage = document.querySelector('.story-page');
    if (storyPage) {
        const storyId = new URLSearchParams(window.location.search).get('id');
        if (storyId) {
            loadStoryDetail(storyId);
        } else {
            showStoryError();
        }
    }

    if (document.querySelector('.sources-grid')) {
        loadSources();
    }

    // Topic filtering (homepage)
    const topicButtons = document.querySelectorAll('.topic-btn[data-topic]');
    topicButtons.forEach(button => {
        button.addEventListener('click', function () {
            currentTopic = this.getAttribute('data-topic');
            topicButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            inSearchMode = false;
            loadGroupedStories(currentTopic);
        });
    });

    // Bias filtering (sources page)
    const biasButtons = document.querySelectorAll('.topic-btn[data-bias]');
    biasButtons.forEach(button => {
        button.addEventListener('click', function () {
            const bias = this.getAttribute('data-bias');
            biasButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            loadSources(bias);
        });
    });

    // Search
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const q = document.getElementById('search-input').value.trim();
            if (q) {
                runSearch(q);
            } else {
                inSearchMode = false;
                loadGroupedStories(currentTopic);
            }
        });
    }

    // Newsletter
    document.querySelectorAll('.newsletter-form').forEach(form => {
        form.addEventListener('submit', handleNewsletterSubmit);
    });

    // Smooth scroll for in-page anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});


/* ----------------------------- Daily briefing ---------------------------- */

async function loadBriefing() {
    const container = document.getElementById('briefing-container');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/briefing/daily`);
        if (!res.ok) throw new Error('unavailable');
        const b = await res.json();
        if (!b.headline_count) {
            container.innerHTML = '';
            return;
        }
        renderBriefing(container, b);
    } catch (err) {
        container.innerHTML = '';
    }
}

function renderBriefing(container, b) {
    const topStories = b.top_stories.map(s => `
        <li>
            <a href="story.html?id=${s.id}">${escapeHtml(s.title)}</a>
            <span class="briefing-counts">
                <span class="pip pip-left">${s.left_count}</span>
                <span class="pip pip-centre">${s.centre_count}</span>
                <span class="pip pip-right">${s.right_count}</span>
            </span>
        </li>`).join('');

    const consensus = b.consensus.length
        ? b.consensus.map(t => `<li>${escapeHtml(t)}</li>`).join('')
        : '<li class="muted">No clear consensus stories today</li>';

    const divisive = b.most_divisive.length
        ? b.most_divisive.map(t => `<li>${escapeHtml(t)}</li>`).join('')
        : '<li class="muted">No sharply divided stories today</li>';

    const topics = b.topics_covered.map(t => `<span class="briefing-topic">${escapeHtml(capitalise(t))}</span>`).join('');

    container.innerHTML = `
        <div class="briefing-card">
            <div class="briefing-head">
                <div>
                    <h2>Daily Briefing</h2>
                    <span class="briefing-date">${escapeHtml(b.date)} · ${b.headline_count} stories tracked</span>
                </div>
                <div class="briefing-topics">${topics}</div>
            </div>
            <div class="briefing-grid">
                <div class="briefing-col">
                    <h4>Top Stories</h4>
                    <ul class="briefing-stories">${topStories}</ul>
                </div>
                <div class="briefing-col">
                    <h4>Where Left &amp; Right Agree</h4>
                    <ul class="briefing-list">${consensus}</ul>
                    <h4>Most Divisive</h4>
                    <ul class="briefing-list">${divisive}</ul>
                </div>
            </div>
        </div>`;
}


/* ------------------------------- Stories --------------------------------- */

function startAutoRefresh() {
    setInterval(() => {
        if (!inSearchMode) {
            loadBriefing();
            loadGroupedStories(currentTopic);
        }
    }, REFRESH_INTERVAL_MS);
}

async function loadGroupedStories(topic = 'all') {
    const container = document.querySelector('.stories .container');
    if (!container) return;

    const url = topic === 'all'
        ? `${API_BASE}/stories/grouped`
        : `${API_BASE}/stories/grouped?topic=${encodeURIComponent(topic)}`;

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('API not available');
        renderGroupedStories(container, await res.json());
    } catch (err) {
        container.innerHTML = errorBox('Could not reach the API. Make sure the backend is running on port 8000.');
    }
}

function renderGroupedStories(container, data) {
    let html = `
        <div class="stories-header">
            <div class="stories-meta">
                <span class="total-count">${data.total_stories} stories</span>
                <span class="last-updated">Updated ${formatTime(data.last_updated)}</span>
                <button onclick="fetchNews(this)" class="btn btn-secondary btn-sm">Refresh Now</button>
            </div>
        </div>`;

    let hasAny = false;
    data.sections.forEach(section => {
        if (!section.stories.length) return;
        hasAny = true;
        html += `
            <div class="story-section" id="section-${section.key}">
                <h2 class="section-title">${escapeHtml(section.title)} <span class="section-count">(${section.stories.length})</span></h2>
                <div class="stories-list">
                    ${section.stories.map(renderStoryCard).join('')}
                </div>
            </div>`;
    });

    if (!hasAny) {
        html += emptyBox();
    }

    container.innerHTML = html;
    animateCards();
}

function renderStoryCard(story) {
    const agreement = story.agreement_preview
        ? `<span class="label">They agree:</span> ${escapeHtml(story.agreement_preview)}`
        : '';
    return `
        <article class="story-card" data-topic="${escapeHtml(story.topic)}">
            <div class="story-header">
                <span class="story-topic">${escapeHtml(capitalise(story.topic))}</span>
                <span class="story-time">${escapeHtml(story.time_ago)}</span>
            </div>
            <h3 class="story-title">
                <a href="story.html?id=${story.id}">${escapeHtml(story.title)}</a>
            </h3>
            <p class="story-summary">${escapeHtml(story.neutral_summary || 'Summary pending…')}</p>

            <div class="perspectives">
                <div class="perspective perspective-left">
                    <span class="perspective-label">Left</span>
                    <p>${escapeHtml(truncate(story.left_perspective.summary, 110))}</p>
                    <span class="source-count">${story.left_perspective.source_count} sources</span>
                </div>
                <div class="perspective perspective-centre">
                    <span class="perspective-label">Centre</span>
                    <p>${escapeHtml(truncate(story.centre_perspective.summary, 110))}</p>
                    <span class="source-count">${story.centre_perspective.source_count} sources</span>
                </div>
                <div class="perspective perspective-right">
                    <span class="perspective-label">Right</span>
                    <p>${escapeHtml(truncate(story.right_perspective.summary, 110))}</p>
                    <span class="source-count">${story.right_perspective.source_count} sources</span>
                </div>
            </div>

            <div class="story-footer">
                <div class="agreement-preview">${agreement}</div>
                <a href="story.html?id=${story.id}" class="read-more">Full Analysis →</a>
            </div>
        </article>`;
}


/* --------------------------------- Search -------------------------------- */

async function runSearch(query) {
    const container = document.querySelector('.stories .container');
    if (!container) return;
    inSearchMode = true;

    try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        if (!res.ok) throw new Error('search failed');
        renderSearchResults(container, query, await res.json());
    } catch (err) {
        container.innerHTML = errorBox('Search is unavailable right now.');
    }
}

function renderSearchResults(container, query, results) {
    let html = `
        <div class="stories-header">
            <div class="stories-meta">
                <span class="total-count">${results.length} result${results.length === 1 ? '' : 's'} for “${escapeHtml(query)}”</span>
                <button onclick="clearSearch()" class="btn btn-secondary btn-sm">Clear</button>
            </div>
        </div>`;

    if (!results.length) {
        html += emptyBox('No matches found. Try a different search.');
        container.innerHTML = html;
        return;
    }

    html += '<div class="stories-list">';
    results.forEach(r => {
        if (r.type === 'story') {
            html += `
                <a class="search-result" href="story.html?id=${r.id}">
                    <span class="result-type">Story</span>
                    <span class="result-title">${escapeHtml(r.title)}</span>
                    <span class="result-snippet">${escapeHtml(r.snippet || '')}</span>
                </a>`;
        } else {
            html += `
                <a class="search-result" href="${escapeHtml(r.url || '#')}" target="_blank" rel="noopener">
                    <span class="result-type result-${getBiasGroup(r.source_bias)}">${escapeHtml(r.source_name || 'Article')}</span>
                    <span class="result-title">${escapeHtml(r.title)}</span>
                    <span class="result-snippet">${escapeHtml(r.snippet || '')}</span>
                </a>`;
        }
    });
    html += '</div>';
    container.innerHTML = html;
    animateCards();
}

function clearSearch() {
    inSearchMode = false;
    const input = document.getElementById('search-input');
    if (input) input.value = '';
    loadGroupedStories(currentTopic);
}


/* ----------------------------- Story detail ------------------------------ */

async function loadStoryDetail(storyId) {
    try {
        const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyId)}`);
        if (!res.ok) throw new Error('Story not found');
        renderStoryDetail(await res.json());
    } catch (err) {
        showStoryError();
    }
}

function renderStoryDetail(story) {
    setText('story-title', story.title);
    setText('story-topic', capitalise(story.topic));
    setText('story-meta-time', `Updated ${story.time_ago} · ${story.article_count} sources`);
    document.title = `${story.title} - International Affairs`;

    const c = story.comparison;
    setText('neutral-summary', c.neutral_summary || 'No summary available yet.');
    setText('left-framing', c.left_framing || 'No left-leaning coverage yet.');
    setText('right-framing', c.right_framing || 'No right-leaning coverage yet.');

    fillList('agreements', c.agreements, 'No shared points identified yet.');
    fillList('disagreements', c.disagreements, 'No clear disagreements identified yet.');
    fillList('left-blind', c.left_blind_spots, 'No notable gaps identified.');
    fillList('right-blind', c.right_blind_spots, 'No notable gaps identified.');

    const sourceList = document.getElementById('source-list');
    if (sourceList) {
        sourceList.innerHTML = story.articles.map(a => `
            <a href="${escapeHtml(a.url)}" target="_blank" rel="noopener" class="source-item">
                <div class="source-info">
                    <div class="source-name">${escapeHtml(a.source_name)}</div>
                    <div class="source-headline">“${escapeHtml(truncate(a.title, 90))}”</div>
                </div>
                <span class="source-bias ${getBiasGroup(a.source_bias)}">${escapeHtml(capitalise(a.source_bias))}</span>
            </a>`).join('');
    }
    setText('source-count-label', `(${story.article_count})`);

    toggle('story-loading', false);
    toggle('story-content', true);
}

function showStoryError() {
    toggle('story-loading', false);
    toggle('story-content', false);
    toggle('story-error', true);
    setText('story-title', 'Story unavailable');
    setText('story-meta-time', '');
    setText('story-topic', '');
}


/* -------------------------------- Sources -------------------------------- */

async function loadSources(bias = 'all') {
    const grid = document.querySelector('.sources-grid');
    if (!grid) return;

    const url = bias === 'all'
        ? `${API_BASE}/sources`
        : `${API_BASE}/sources?bias=${encodeURIComponent(bias)}`;

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('API not available');
        renderSources(grid, await res.json());
    } catch (err) {
        grid.innerHTML = errorBox('Could not load sources. Make sure the backend is running.');
    }
}

function renderSources(grid, sources) {
    grid.innerHTML = sources.map(source => {
        const biasIndex = getBiasIndex(source.bias_category);
        const dots = [0, 1, 2, 3, 4].map(i =>
            `<span class="bias-dot ${i === biasIndex ? 'active ' + getBiasClass(i) : ''}"></span>`
        ).join('');

        return `
            <div class="source-card" data-bias="${getBiasGroup(source.bias_category)}">
                <div class="source-card-header">
                    <div>
                        <h3>${escapeHtml(source.name)}</h3>
                        <p class="source-card-country">${escapeHtml(source.country || '')}</p>
                    </div>
                    <span class="source-bias ${getBiasGroup(source.bias_category)}">${escapeHtml(capitalise(source.bias_category))}</span>
                </div>
                <p class="source-card-description">${escapeHtml(source.description || '')}</p>
                <div class="bias-indicator">
                    ${dots}
                    <span class="bias-label">${escapeHtml(capitalise(source.bias_category))}</span>
                </div>
            </div>`;
    }).join('');
    animateCards();
}


/* ------------------------------ Newsletter ------------------------------- */

async function handleNewsletterSubmit(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const emailInput = form.querySelector('input[type="email"]');
    const button = form.querySelector('button');
    const originalText = button.textContent;

    try {
        const res = await fetch(`${API_BASE}/newsletter/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailInput.value })
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok) {
            button.textContent = data.already_subscribed ? 'Already subscribed' : 'Subscribed!';
            button.style.background = '#4CAF50';
            emailInput.value = '';
        } else {
            button.textContent = data.detail || 'Invalid email';
            button.style.background = '#c0392b';
        }
    } catch (err) {
        button.textContent = 'Try again later';
        button.style.background = '#c0392b';
    }

    setTimeout(() => {
        button.textContent = originalText;
        button.style.background = '';
    }, 3000);
}


/* -------------------------------- Actions -------------------------------- */

async function fetchNews(btn) {
    if (btn) { btn.disabled = true; btn.textContent = 'Fetching…'; }
    try {
        const res = await fetch(`${API_BASE}/fetch-news`, { method: 'POST' });
        if (!res.ok) throw new Error('failed');
        setTimeout(() => {
            loadBriefing();
            loadGroupedStories(currentTopic);
            if (btn) { btn.disabled = false; btn.textContent = 'Refresh Now'; }
        }, 6000);
    } catch (err) {
        if (btn) { btn.disabled = false; btn.textContent = 'Refresh Now'; }
        alert('Could not connect to the API. Make sure the backend is running.');
    }
}


/* -------------------------------- Helpers -------------------------------- */

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value || '';
}

function fillList(id, items, emptyMessage) {
    const el = document.getElementById(id);
    if (!el) return;
    if (items && items.length) {
        el.innerHTML = items.map(i => `<li>${escapeHtml(i)}</li>`).join('');
    } else {
        el.innerHTML = `<li class="muted">${escapeHtml(emptyMessage || '—')}</li>`;
    }
}

function toggle(id, show) {
    const el = document.getElementById(id);
    if (el) el.hidden = !show;
}

function capitalise(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length).trimEnd() + '…' : str;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    if (isNaN(date)) return 'just now';
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function getBiasIndex(category) {
    return { 'left': 0, 'centre-left': 1, 'centre': 2, 'centre-right': 3, 'right': 4 }[category] ?? 2;
}

function getBiasClass(index) {
    return ['left', 'centre-left', 'centre', 'centre-right', 'right'][index];
}

function getBiasGroup(category) {
    if (['left', 'centre-left'].includes(category)) return 'left';
    if (category === 'centre') return 'centre';
    return 'right';
}

function errorBox(message) {
    return `<div class="state-box error">${escapeHtml(message)}</div>`;
}

function emptyBox(message) {
    return `
        <div class="state-box">
            <p>${escapeHtml(message || 'No stories yet. Fetch news to populate the site.')}</p>
            <button onclick="fetchNews(this)" class="btn btn-primary" style="margin-top:16px;">Fetch News Now</button>
        </div>`;
}

function animateCards() {
    document.querySelectorAll('.story-card, .source-card, .search-result').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(16px)';
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, Math.min(index * 60, 600));
    });
}
