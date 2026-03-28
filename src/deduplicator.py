"""Two-stage article deduplication with URL match and Gemini CLI."""

import logging
import os
from typing import Dict, List
from urllib.parse import urlparse, urlunparse

import subprocess

try:
    from . import Article
    from .config import AppConfig
except ImportError:  # pragma: no cover
    from __init__ import Article
    from config import AppConfig


class DeduplicationError(Exception):
    """Raised when deduplication fails and the pipeline should abort."""
    pass


def _normalize_url(url):
    # type: (str) -> str
    """Strip query string and fragment for deduplication key.

    WSJ and other publishers distribute the same article across multiple RSS feeds
    with different tracking parameters (e.g. ?mod=rss_markets_main vs
    ?mod=pls_whats_news_us_business_f). Stripping these ensures they are
    recognised as duplicates in Stage 1 before Gemini is invoked.
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _dedup_by_exact_url(articles):
    # type: (List[Article]) -> List[Article]
    by_url = {}  # type: Dict[str, Article]
    for article in articles:
        key = _normalize_url(article.link)
        existing = by_url.get(key)
        if existing is None or article.published > existing.published:
            by_url[key] = article
    return list(by_url.values())


def _build_prompt(lines, preferred_sources, model):
    # type: (List[str], List[str], str) -> str
    preferred_sources_text = ", ".join(preferred_sources) if preferred_sources else "なし"
    numbered_list = "\n".join(lines)
    return (
        "ソフトウェア開発のデータ処理タスクとして、以下のテキストリストを処理してください。\n"
        "以下はニュース記事のタイトル一覧です（番号. タイトル (ソース) の形式）。\n"
        "同じニュースを報じている記事をグループ化し、各グループから1記事だけ残してください。\n"
        "残す記事の選択基準（優先順）:\n"
        f"  1. preferred_sources（{preferred_sources_text}）に含まれるソースがあればその中で最新のもの\n"
        "  2. なければグループ内で最新のもの\n"
        "出力は残す記事の番号のみをカンマ区切りで返してください。説明文は不要です。\n"
        "例: 1,3,5,8,12\n"
        f"使用モデル: {model}\n\n"
        f"{numbered_list}"
    )


def _parse_indices(output, max_index):
    # type: (str, int) -> List[int]
    if not output:
        raise ValueError("Gemini output is empty")

    selected = []  # type: List[int]
    seen = set()  # type: set
    for token in output.split(","):
        value = token.strip()
        if not value:
            continue
        if not value.isdigit():
            raise ValueError(f"Invalid index token: {value}")
        index = int(value)
        if index < 1 or index > max_index:
            raise ValueError(f"Index out of range: {index}")
        zero_based = index - 1
        if zero_based not in seen:
            seen.add(zero_based)
            selected.append(zero_based)

    if not selected:
        raise ValueError("No valid indices in Gemini output")
    return selected


def _deduplicate_batch(articles, preferred_sources, model):
    # type: (List[Article], List[str], str) -> List[Article]
    lines = [f"{i + 1}. {article.title} ({article.source})" for i, article in enumerate(articles)]
    prompt = _build_prompt(lines, preferred_sources, model)
    result = subprocess.run(
        ["/home/naohisa-harada/.nvm/versions/node/v22.22.1/bin/gemini", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=300,
        env=os.environ.copy(),
    )
    result.check_returncode()
    indices = _parse_indices(result.stdout.strip(), len(articles))
    return [articles[i] for i in indices]


def _deduplicate_by_gemini(articles, preferred_sources, model, dedup_batch_size):
    # type: (List[Article], List[str], str, int) -> List[Article]
    if len(articles) <= 1:
        return articles

    sorted_articles = sorted(articles, key=lambda a: (a.title or "").casefold())
    deduplicated = []  # type: List[Article]
    for start in range(0, len(sorted_articles), dedup_batch_size):
        batch = sorted_articles[start : start + dedup_batch_size]
        deduplicated.extend(_deduplicate_batch(batch, preferred_sources, model))
    return deduplicated


def deduplicate_articles(articles, config):
    # type: (List[Article], AppConfig) -> List[Article]
    # --- テスト用の記事を注入（検証時にこのブロックのコメントアウトを解除） ---
    # try:
    #     from tests.test_data_template import generated_test_articles
    #     articles = generated_test_articles
    #     logging.info("--- Injected test articles from tests/test_data_template.py ---")
    # except ImportError:
    #     logging.error("--- Failed to import tests/test_data_template.py. ---")
    #     pass
    # --- ここまで ---
    if not articles:
        return []

    stage1 = _dedup_by_exact_url(articles)
    logging.info("[Deduplicator] Stage 1 URL dedup: %s -> %s", len(articles), len(stage1))

    SECOND_PASS_BATCH_SIZE = 100

    try:
        # Stage 2a: 通常バッチで重複削除
        stage2a = _deduplicate_by_gemini(
            articles=stage1,
            preferred_sources=config.deduplication.preferred_sources,
            model=config.gemini.model,
            dedup_batch_size=config.gemini.dedup_batch_size,
        )
        logging.info("[Deduplicator] Stage 2a title clustering: %s -> %s", len(stage1), len(stage2a))

        # Stage 2b: 大きなバッチで境界をまたいだ重複を削除
        stage2b = _deduplicate_by_gemini(
            articles=stage2a,
            preferred_sources=config.deduplication.preferred_sources,
            model=config.gemini.model,
            dedup_batch_size=SECOND_PASS_BATCH_SIZE,
        )
        stage2b.sort(key=lambda a: a.published, reverse=True)
        logging.info("[Deduplicator] Stage 2b wide-batch clustering: %s -> %s", len(stage2a), len(stage2b))
        return stage2b
    except Exception as exc:
        stderr = getattr(exc, "stderr", None)
        msg = f"Stage 2 Gemini deduplication failed: {exc} | stderr: {stderr}"
        if config.deduplication.on_dedup_failure == "send_anyway":
            stage1.sort(key=lambda a: a.published, reverse=True)
            logging.warning("[Deduplicator] %s. Returning Stage 1 output.", msg)
            return stage1
        logging.error("[Deduplicator] %s", msg)
        raise DeduplicationError(msg)
