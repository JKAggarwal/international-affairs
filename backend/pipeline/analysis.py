"""Generate the left/right comparison for a story cluster.

Two modes:
  * Heuristic (default, no API key needed): derives framing, shared themes and
    blind spots from the vocabulary and entities each side emphasises.
  * LLM (optional): if OPENAI_API_KEY is set, sends the grouped article
    summaries to the OpenAI Chat Completions API for a richer analysis and
    falls back to the heuristic on any error.

Both modes return the same dict shape so the rest of the pipeline is agnostic.
"""
import json
import os
import re
from typing import Dict, List

from . import nlp
from .clustering import ArticleLike

LEFT_BIASES = {"left", "centre-left"}
CENTRE_BIASES = {"centre"}
RIGHT_BIASES = {"right", "centre-right"}

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sides(members: List[ArticleLike]):
    left = [m for m in members if m.bias_category in LEFT_BIASES]
    centre = [m for m in members if m.bias_category in CENTRE_BIASES]
    right = [m for m in members if m.bias_category in RIGHT_BIASES]
    return left, centre, right


def _first_sentences(text: str, max_chars: int = 320) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    sentences = _SENTENCE_RE.split(text)
    out = ""
    for s in sentences:
        if len(out) + len(s) > max_chars:
            break
        out = f"{out} {s}".strip()
    return out or text[:max_chars].rsplit(" ", 1)[0] + "…"


def _representative_summary(articles: List[ArticleLike]) -> str:
    summaries = [a.summary for a in articles if a.summary]
    if not summaries:
        return ""
    # The longest summary tends to be the most descriptive.
    return max(summaries, key=len)


def _phrase_list(terms: List[str]) -> str:
    terms = [t for t in terms if t]
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]
    return ", ".join(terms[:-1]) + f" and {terms[-1]}"


def _source_names(articles: List[ArticleLike], source_lookup: Dict[int, str]) -> List[str]:
    names = []
    for a in articles:
        name = source_lookup.get(a.id)
        if name and name not in names:
            names.append(name)
    return names


def heuristic_comparison(
    members: List[ArticleLike],
    source_lookup: Dict[int, str],
) -> Dict:
    left, centre, right = _split_sides(members)

    all_text = [f"{m.title}. {m.summary or ''}" for m in members]
    idf = nlp.build_idf([nlp.tokenize(t) for t in all_text])

    left_text = [f"{m.title}. {m.summary or ''}" for m in left]
    right_text = [f"{m.title}. {m.summary or ''}" for m in right]

    left_kw = nlp.keywords(left_text, idf, top_n=10) if left_text else []
    right_kw = nlp.keywords(right_text, idf, top_n=10) if right_text else []

    left_set, right_set = set(left_kw), set(right_kw)
    shared = [k for k in left_kw if k in right_set]
    left_only = [k for k in left_kw if k not in right_set]
    right_only = [k for k in right_kw if k not in left_set]

    left_entities = set()
    for m in left:
        left_entities |= set(nlp.extract_entities(f"{m.title}. {m.summary or ''}"))
    right_entities = set()
    for m in right:
        right_entities |= set(nlp.extract_entities(f"{m.title}. {m.summary or ''}"))
    shared_entities = sorted(left_entities & right_entities)

    # Neutral summary: prefer a centre source, else the fullest summary.
    neutral = _representative_summary(centre) or _representative_summary(members)
    neutral = _first_sentences(neutral, 360) or "Multiple outlets are covering this developing story."

    left_names = _source_names(left, source_lookup)
    right_names = _source_names(right, source_lookup)

    if left:
        left_themes = _phrase_list((left_only or left_kw)[:5]) or "the core developments"
        left_framing = (
            f"Left-leaning outlets ({_phrase_list(left_names)}) emphasise themes such as "
            f"{left_themes}. {_first_sentences(_representative_summary(left), 200)}"
        ).strip()
    else:
        left_framing = "No left-leaning sources have covered this story yet."

    if right:
        right_themes = _phrase_list((right_only or right_kw)[:5]) or "the core developments"
        right_framing = (
            f"Right-leaning outlets ({_phrase_list(right_names)}) emphasise themes such as "
            f"{right_themes}. {_first_sentences(_representative_summary(right), 200)}"
        ).strip()
    else:
        right_framing = "No right-leaning sources have covered this story yet."

    agreements = []
    if shared_entities:
        agreements.append(f"Both sides reference {_phrase_list(shared_entities[:4])}")
    if shared:
        agreements.append(f"Shared focus on {_phrase_list(shared[:4])}")
    if not agreements:
        agreements.append("Both sides report the same underlying event")

    disagreements = []
    if left_only and right_only:
        disagreements.append(
            f"Left frames it around {_phrase_list(left_only[:3])}; "
            f"right frames it around {_phrase_list(right_only[:3])}"
        )
    if left_only:
        disagreements.append(f"Left uniquely highlights {_phrase_list(left_only[:3])}")
    if right_only:
        disagreements.append(f"Right uniquely highlights {_phrase_list(right_only[:3])}")
    if not disagreements:
        disagreements.append("Emphasis and tone differ between outlets")

    left_blind = []
    right_only_entities = sorted(right_entities - left_entities)
    if right_only:
        left_blind.append(f"Gives little attention to {_phrase_list(right_only[:4])}")
    if right_only_entities:
        left_blind.append(f"Rarely mentions {_phrase_list(right_only_entities[:3])}")
    if not left_blind:
        left_blind.append("Coverage broadly overlaps with the right on this story")

    right_blind = []
    left_only_entities = sorted(left_entities - right_entities)
    if left_only:
        right_blind.append(f"Gives little attention to {_phrase_list(left_only[:4])}")
    if left_only_entities:
        right_blind.append(f"Rarely mentions {_phrase_list(left_only_entities[:3])}")
    if not right_blind:
        right_blind.append("Coverage broadly overlaps with the left on this story")

    return {
        # The heuristic mode does not synthesise a headline; the pipeline keeps
        # the representative outlet headline in that case.
        "headline": None,
        "neutral_summary": neutral,
        "left_framing": left_framing,
        "right_framing": right_framing,
        "agreements": agreements[:5],
        "disagreements": disagreements[:5],
        "left_blind_spots": left_blind[:4],
        "right_blind_spots": right_blind[:4],
        "method": "heuristic",
    }


def _clean_headline(value) -> str | None:
    """Sanitise an LLM-generated headline; return None if unusable.

    Guards against the model returning quoted text, a trailing " - Source"
    attribution, empty strings, or an over-long paragraph. On any failure the
    caller falls back to a real outlet headline.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().strip('"').strip("'").strip()
    # Drop a trailing source attribution like " - Reuters" or " | BBC News".
    text = re.split(r"\s+[\u2013\u2014\-|]\s+", text)[0].strip() if " - " in text or " | " in text else text
    if not text:
        return None
    # A neutral headline should be short; reject paragraphs.
    if len(text) > 120 or len(text.split()) > 18:
        return None
    return text


def _build_llm_prompt(members: List[ArticleLike], source_lookup: Dict[int, str]) -> str:
    left, centre, right = _split_sides(members)

    def block(label, articles):
        if not articles:
            return f"{label}:\n- (none)\n"
        lines = [f"{label}:"]
        for a in articles:
            name = source_lookup.get(a.id, "Unknown")
            lines.append(f"- {name}: {a.title}. {(a.summary or '')[:300]}")
        return "\n".join(lines) + "\n"

    return (
        "You are an expert media analyst comparing coverage of the same "
        "international affairs story across the political spectrum.\n\n"
        + block("LEFT-LEANING SOURCES", left)
        + block("CENTRE SOURCES", centre)
        + block("RIGHT-LEANING SOURCES", right)
        + "\nReturn ONLY valid JSON with these keys: headline (string), "
        "neutral_summary (string), left_framing (string), right_framing "
        "(string), agreements (array of strings), disagreements (array of "
        "strings), left_blind_spots (array of strings), right_blind_spots "
        "(array of strings). Be balanced and fair.\n"
        "The headline must be a single, neutral, factual headline of at most 12 "
        "words that summarises the underlying event without loaded language, "
        "spin or opinion, and that outlets on both the left and right would "
        "accept as accurate. Do not use quotation marks or a trailing source name."
    )


def llm_comparison(members: List[ArticleLike], source_lookup: Dict[int, str]) -> Dict:
    """Call OpenAI if configured. Raises on any failure so callers can fall back."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    import httpx

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = _build_llm_prompt(members, source_lookup)

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    data["method"] = f"llm:{model}"

    data["headline"] = _clean_headline(data.get("headline"))

    # Coerce string fields so a null from the model never breaks serialization.
    for key in ("neutral_summary", "left_framing", "right_framing"):
        value = data.get(key)
        data[key] = value.strip() if isinstance(value, str) and value.strip() else None

    for key in ("agreements", "disagreements", "left_blind_spots", "right_blind_spots"):
        if not isinstance(data.get(key), list):
            data[key] = [str(data.get(key))] if data.get(key) else []
    return data


def generate_comparison(members: List[ArticleLike], source_lookup: Dict[int, str]) -> Dict:
    """Produce a comparison, preferring the LLM when available."""
    if os.getenv("OPENAI_API_KEY"):
        try:
            return llm_comparison(members, source_lookup)
        except Exception as e:  # noqa: BLE001 - fall back to heuristic on any error
            print(f"  LLM comparison failed ({e}); using heuristic")
    return heuristic_comparison(members, source_lookup)
