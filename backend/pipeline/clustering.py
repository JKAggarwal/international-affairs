"""Group articles that cover the same underlying story.

Strategy (dependency-free):
  1. Build a TF-IDF model over the candidate articles (title weighted heavily).
  2. Greedily assign each article to the most similar existing cluster, using
     cosine similarity blended with proper-noun (entity) overlap.
  3. Start a new cluster when nothing is similar enough.

The public surface is `cluster_articles(items)` which takes lightweight
`ArticleLike` objects and returns a list of `Cluster` objects. This keeps the
algorithm decoupled from SQLAlchemy so it can be unit-tested in isolation.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from . import nlp


def _primary(topic: Optional[str]) -> str:
    """First (primary) topic of a possibly comma-separated topic string."""
    return (topic or "general").split(",")[0]


@dataclass
class ArticleLike:
    id: int
    title: str
    summary: str
    topic: str
    bias_category: str

    def text(self) -> str:
        # Title is repeated to weight it more heavily than the summary.
        return f"{self.title} {self.title} {self.summary or ''}"


@dataclass
class Cluster:
    article_ids: List[int] = field(default_factory=list)
    members: List[ArticleLike] = field(default_factory=list)
    centroid: Dict[str, float] = field(default_factory=dict)
    entities: Set[str] = field(default_factory=set)
    topic: Optional[str] = None

    def add(self, article: ArticleLike, vector: Dict[str, float], entities: Set[str]):
        n = len(self.members)
        # Running average of the TF-IDF vectors -> cluster centroid.
        for term, weight in self.centroid.items():
            self.centroid[term] = weight * n / (n + 1)
        for term, weight in vector.items():
            self.centroid[term] = self.centroid.get(term, 0.0) + weight / (n + 1)
        self.entities |= entities
        self.members.append(article)
        self.article_ids.append(article.id)
        if self.topic is None or self.topic == "general":
            self.topic = article.topic

    def bias_categories(self) -> Set[str]:
        return {m.bias_category for m in self.members}

    def has_left(self) -> bool:
        return bool(self.bias_categories() & {"left", "centre-left"})

    def has_right(self) -> bool:
        return bool(self.bias_categories() & {"right", "centre-right"})

    def source_count(self) -> int:
        return len(self.members)


# Tuning knobs. Titles are short, so cosine scores run low. Same-story articles
# almost always share a proper noun (a person, place or organisation), so we
# require entity overlap for normal merges and only allow entity-less merges
# when the vocabulary similarity is very high. This prevents topic-only blobs.
ENTITY_MERGE_SIMILARITY = 0.18   # merge when ≥1 shared entity and this much overlap
NOENTITY_MERGE_SIMILARITY = 0.45  # merge without shared entity only if very similar
MIN_SHARED_TOKENS = 2


def cluster_articles(items: List[ArticleLike]) -> List[Cluster]:
    if not items:
        return []

    tokenized = [nlp.tokenize(a.text()) for a in items]
    idf = nlp.build_idf(tokenized)
    vectors = [nlp.tfidf_vector(toks, idf) for toks in tokenized]
    entities = [set(nlp.extract_entities(f"{a.title}. {a.summary or ''}")) for a in items]
    token_sets = [set(toks) for toks in tokenized]

    clusters: List[Cluster] = []

    for idx, article in enumerate(items):
        vector = vectors[idx]
        ents = entities[idx]
        tokens = token_sets[idx]

        best_cluster: Optional[Cluster] = None
        best_score = 0.0

        for cluster in clusters:
            # Same story => same primary topic. Compare the primary (first)
            # topic so multi-topic tags (e.g. "security,uk") still merge with
            # same-theme articles while avoiding cross-topic blobs.
            if _primary(cluster.topic) != _primary(article.topic):
                continue

            sim = nlp.cosine_similarity(vector, cluster.centroid)
            entity_overlap = len(ents & cluster.entities)
            shared_tokens = len(tokens & set(cluster.centroid.keys()))

            if entity_overlap >= 1:
                ok = sim >= ENTITY_MERGE_SIMILARITY and shared_tokens >= MIN_SHARED_TOKENS
            else:
                ok = sim >= NOENTITY_MERGE_SIMILARITY and shared_tokens >= MIN_SHARED_TOKENS + 1

            score = sim + 0.05 * entity_overlap
            if ok and score > best_score:
                best_score = score
                best_cluster = cluster

        if best_cluster is not None:
            best_cluster.add(article, vector, ents)
        else:
            new_cluster = Cluster(topic=article.topic)
            new_cluster.add(article, vector, ents)
            clusters.append(new_cluster)

    return clusters


def is_publishable(cluster: Cluster) -> bool:
    """A story is worth showing if at least two distinct sources cover it."""
    distinct_sources = len(cluster.article_ids)
    return distinct_sources >= 2
