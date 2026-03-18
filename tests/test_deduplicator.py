from datetime import datetime, timedelta, timezone
import subprocess
from unittest.mock import MagicMock

import pytest

from src import Article
from src.config import (
    AppConfig,
    DeduplicationConfig,
    EmailConfig,
    FeedConfig,
    GeminiConfig,
    OutputConfig,
    ScheduleConfig,
    SystemConfig,
)
from src.deduplicator import DeduplicationError, _dedup_by_exact_url, _normalize_url, deduplicate_articles


def _dt(hours_ago=0):
    return datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc) - timedelta(hours=hours_ago)


def _article(title, link, source="Source", hours_ago=0):
    return Article(title=title, link=link, published=_dt(hours_ago), source=source, category="Tech")


def _config(preferred_sources=None, on_dedup_failure="send_anyway"):
    return AppConfig(
        feeds=FeedConfig(opml_file="feedly_rss.opml", timeout_seconds=10, skip_feedly_proxy=True),
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
        gemini=GeminiConfig(model="gemini-2.0-flash", dedup_batch_size=80),
        deduplication=DeduplicationConfig(
            preferred_sources=preferred_sources or [],
            on_dedup_failure=on_dedup_failure,
        ),
        email=EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="a@example.com",
            sender_password="pw",
            recipients=["b@example.com"],
            max_articles_per_email=200,
        ),
        output=OutputConfig(save_html=True, html_dir="./output", log_file="./logs/news_filter.log", state_file="./state/last_run.json"),
        system=SystemConfig(poweroff_after_run=False),
    )


def test_ut_004_1_remove_duplicate_urls():
    articles = [
        _article("a1", "https://example.com/1", hours_ago=2),
        _article("a2", "https://example.com/1", hours_ago=1),
        _article("a3", "https://example.com/2", hours_ago=1),
    ]

    deduped = _dedup_by_exact_url(articles)

    assert len(deduped) == 2


def test_ut_004_2_keep_most_recent():
    old = _article("old", "https://example.com/1", hours_ago=3)
    new = _article("new", "https://example.com/1", hours_ago=1)

    deduped = _dedup_by_exact_url([old, new])

    assert deduped == [new]


def test_ut_004_4_remove_query_param_duplicates():
    """Same base URL with different ?mod= tracking params should be deduplicated.

    Reproduces the WSJ multi-feed duplicate pattern observed on 2026-03-18:
    e.g. .../eea7029e vs .../eea7029e?mod=pls_whats_news_us_business_f
    """
    articles = [
        _article("old",    "https://www.wsj.com/article/xyz", hours_ago=3),
        _article("recent", "https://www.wsj.com/article/xyz?mod=rss_markets_main", hours_ago=2),
        _article("newest", "https://www.wsj.com/article/xyz?mod=pls_whats_news_us_business_f", hours_ago=1),
    ]

    deduped = _dedup_by_exact_url(articles)

    assert len(deduped) == 1
    assert deduped[0].title == "newest"


def test_ut_004_5_normalize_url_strips_query_and_fragment():
    assert _normalize_url("https://example.com/a?foo=1&bar=2#section") == "https://example.com/a"
    assert _normalize_url("https://example.com/a") == "https://example.com/a"
    assert _normalize_url("https://example.com/a#only-fragment") == "https://example.com/a"


def test_ut_004_3_handle_all_unique():
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    deduped = _dedup_by_exact_url(articles)

    assert len(deduped) == 2


def test_ut_005_1_cluster_similar_titles(monkeypatch):
    articles = [
        _article("Apple releases iOS 18", "https://example.com/1", hours_ago=1),
        _article("Apple releases iOS 18 today", "https://example.com/2", hours_ago=2),
    ]

    mock_result = MagicMock()
    mock_result.stdout = "1"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)

    deduped = deduplicate_articles(articles, _config())

    assert len(deduped) == 1


def test_ut_005_2_keep_different_titles(monkeypatch):
    articles = [
        _article("Apple news", "https://example.com/1", hours_ago=1),
        _article("Fed rates", "https://example.com/2", hours_ago=2),
    ]

    mock_result = MagicMock()
    mock_result.stdout = "1,2"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)

    deduped = deduplicate_articles(articles, _config())

    assert len(deduped) == 2


def test_ut_005_3_prefer_preferred_source(monkeypatch):
    articles = [
        _article("Market update", "https://example.com/1", source="Reuters", hours_ago=3),
        _article("Market update", "https://example.com/2", source="Other", hours_ago=1),
    ]

    mock_result = MagicMock()
    mock_result.stdout = "1"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)

    deduped = deduplicate_articles(articles, _config(preferred_sources=["Reuters"]))

    assert len(deduped) == 1
    assert deduped[0].source == "Reuters"


def test_ut_005_4_prefer_recent_if_no_preferred(monkeypatch):
    older = _article("Cluster", "https://example.com/1", source="A", hours_ago=3)
    newer = _article("Cluster", "https://example.com/2", source="B", hours_ago=1)

    mock_result = MagicMock()
    mock_result.stdout = "2"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)

    deduped = deduplicate_articles([older, newer], _config(preferred_sources=[]))

    assert len(deduped) == 1
    assert deduped[0].link == newer.link


def test_ut_005_5_handle_gemini_timeout(monkeypatch):
    articles = [_article("a", "https://example.com/1", hours_ago=3), _article("b", "https://example.com/2", hours_ago=1)]

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["gemini"], timeout=60)

    monkeypatch.setattr("src.deduplicator.subprocess.run", raise_timeout)

    with pytest.raises(DeduplicationError):
        deduplicate_articles(articles, _config(on_dedup_failure="fail"))


def test_ut_005_6_handle_empty_list():
    deduped = deduplicate_articles([], _config())

    assert deduped == []


def test_ut_005_7_on_dedup_failure_fail(monkeypatch):
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    def raise_error(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["gemini"])

    monkeypatch.setattr("src.deduplicator.subprocess.run", raise_error)
    cfg = _config(on_dedup_failure="fail")

    with pytest.raises(DeduplicationError):
        deduplicate_articles(articles, cfg)


def test_ut_005_8_on_dedup_failure_send_anyway(monkeypatch):
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    def raise_error(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["gemini"])

    monkeypatch.setattr("src.deduplicator.subprocess.run", raise_error)
    deduped = deduplicate_articles(articles, _config(on_dedup_failure="send_anyway"))

    assert len(deduped) == len(articles)
