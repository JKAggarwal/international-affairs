"""Lightweight, dependency-free text utilities for clustering and analysis.

These helpers intentionally avoid heavy ML libraries so the pipeline runs
anywhere with just the standard library. If you later add embeddings
(OpenAI / sentence-transformers), the clustering module can swap its
similarity function without touching the rest of the pipeline.
"""
import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Set

# Common English stop words plus newsy filler that adds noise to similarity.
STOP_WORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "has", "have", "had", "he", "her", "his", "how", "in", "into",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "them",
    "they", "this", "to", "was", "were", "what", "when", "where", "which",
    "who", "will", "with", "would", "you", "your", "we", "our", "us", "i",
    "after", "before", "over", "under", "about", "more", "most", "new",
    "says", "say", "said", "amid", "could", "may", "might", "set", "get",
    "gets", "make", "makes", "made", "than", "then", "out", "up", "down",
    "off", "not", "no", "yes", "if", "so", "such", "also", "just", "can",
    "all", "any", "some", "one", "two", "three", "first", "last", "year",
    "years", "day", "days", "week", "time", "report", "reports", "live",
    "news", "latest", "update", "updates", "video", "watch", "opinion",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumerics, drop stop words and short tokens."""
    if not text:
        return []
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def token_set(text: str) -> Set[str]:
    return set(tokenize(text))


def build_idf(documents: List[List[str]]) -> Dict[str, float]:
    """Inverse document frequency across a corpus of tokenized documents."""
    n_docs = len(documents) or 1
    df: Counter = Counter()
    for doc in documents:
        for term in set(doc):
            df[term] += 1
    return {term: math.log(n_docs / (1 + freq)) + 1.0 for term, freq in df.items()}


def tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    """TF-IDF weighted bag-of-words for a single document."""
    if not tokens:
        return {}
    tf = Counter(tokens)
    length = len(tokens)
    return {term: (count / length) * idf.get(term, 1.0) for term, count in tf.items()}


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse weighted vectors."""
    if not a or not b:
        return 0.0
    # Iterate over the smaller vector for the dot product.
    if len(a) > len(b):
        a, b = b, a
    dot = sum(weight * b.get(term, 0.0) for term, weight in a.items())
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    if intersection == 0:
        return 0.0
    return intersection / len(a | b)


# Proper-noun-ish extraction for entity overlap: capitalised words in the
# original (non-lowercased) text, minus the leading word of each sentence
# which is capitalised by grammar rather than because it is a name.
_PROPER_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b")


def extract_entities(text: str, max_entities: int = 12) -> List[str]:
    if not text:
        return []
    candidates = _PROPER_RE.findall(text)
    seen: Dict[str, int] = {}
    for c in candidates:
        key = c.strip()
        if len(key) < 3:
            continue
        if key.lower() in STOP_WORDS:
            continue
        seen[key] = seen.get(key, 0) + 1
    ordered = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in ordered[:max_entities]]


def keywords(texts: Iterable[str], idf: Dict[str, float], top_n: int = 8) -> List[str]:
    """Highest IDF-weighted terms across a group of texts."""
    agg: Counter = Counter()
    for text in texts:
        for term in tokenize(text):
            agg[term] += 1
    scored = [(term, count * idf.get(term, 1.0)) for term, count in agg.items()]
    scored.sort(key=lambda kv: -kv[1])
    return [term for term, _ in scored[:top_n]]
