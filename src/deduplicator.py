"""Two-stage article deduplication with Ollama embeddings."""

import logging
from collections import defaultdict
from typing import Dict, List

import numpy as np
import requests
from sklearn.cluster import AgglomerativeClustering

try:
    from . import Article
    from .config import AppConfig
except ImportError:  # pragma: no cover
    from __init__ import Article
    from config import AppConfig


def _dedup_by_exact_url(articles):
    # type: (List[Article]) -> List[Article]
    by_url = {}  # type: Dict[str, Article]
    for article in articles:
        existing = by_url.get(article.link)
        if existing is None or article.published > existing.published:
            by_url[article.link] = article
    return list(by_url.values())


def _get_embedding(base_url, model, text, timeout_seconds=20):
    # type: (str, str, str, int) -> List[float]
    url = base_url.rstrip("/") + "/api/embeddings"
    resp = requests.post(url, json={"model": model, "prompt": text}, timeout=timeout_seconds)
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("Empty embedding response")
    return embedding


def _pick_representative(cluster_articles, preferred_sources):
    # type: (List[Article], List[str]) -> Article
    if preferred_sources:
        preferred = {s.lower() for s in preferred_sources}
        candidates = [a for a in cluster_articles if a.source.lower() in preferred]
        if candidates:
            return max(candidates, key=lambda a: a.published)
    return max(cluster_articles, key=lambda a: a.published)


def _cluster_by_title_similarity(articles, base_url, model, dedup_threshold, preferred_sources):
    # type: (List[Article], str, str, float, List[str]) -> List[Article]
    if len(articles) <= 1:
        return articles

    embeddings = [
        _get_embedding(base_url=base_url, model=model, text=article.title)
        for article in articles
    ]
    X = np.array(embeddings, dtype=np.float64)

    # cosine distance threshold = 1 - cosine similarity threshold
    distance_threshold = 1 - dedup_threshold
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(X)

    grouped = defaultdict(list)  # type: Dict[int, List[Article]]
    for label, article in zip(labels, articles):
        grouped[int(label)].append(article)

    deduped = [_pick_representative(group, preferred_sources) for group in grouped.values()]
    deduped.sort(key=lambda a: a.published, reverse=True)
    return deduped


def deduplicate_articles(articles, config):
    # type: (List[Article], AppConfig) -> List[Article]
    if not articles:
        return []

    stage1 = _dedup_by_exact_url(articles)
    logging.info("[Deduplicator] Stage 1 URL dedup: %s -> %s", len(articles), len(stage1))

    try:
        stage2 = _cluster_by_title_similarity(
            articles=stage1,
            base_url=config.llm.base_url,
            model=config.llm.embedding_model,
            dedup_threshold=config.llm.dedup_threshold,
            preferred_sources=config.deduplication.preferred_sources,
        )
        logging.info("[Deduplicator] Stage 2 title clustering: %s -> %s", len(stage1), len(stage2))
        return stage2
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            logging.critical("[Deduplicator] Model not found: %s. Aborting.", config.llm.embedding_model)
            raise SystemExit(1)
        return _handle_dedup_failure(config, stage1, exc)
    except Exception as exc:
        return _handle_dedup_failure(config, stage1, exc)


def _handle_dedup_failure(config, stage1, exc):
    # type: (AppConfig, List[Article], Exception) -> List[Article]
    on_failure = config.deduplication.on_dedup_failure
    if on_failure == "fail":
        logging.error("[Deduplicator] Dedup failure and on_dedup_failure=fail; aborting: %s", exc)
        raise SystemExit(1)
    logging.warning("[Deduplicator] Ollama unavailable; fallback without stage2 (on_dedup_failure=send_anyway): %s", exc)
    stage1.sort(key=lambda a: a.published, reverse=True)
    return stage1
