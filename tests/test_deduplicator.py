from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import requests

from src import Article
from src.config import (
    AppConfig,
    DeduplicationConfig,
    EmailConfig,
    FeedConfig,
    LLMConfig,
    OutputConfig,
    ScheduleConfig,
    SystemConfig,
)
from src.deduplicator import DeduplicationError, _dedup_by_exact_url, deduplicate_articles


def _dt(hours_ago=0):
    return datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc) - timedelta(hours=hours_ago)


def _article(title, link, source="Source", hours_ago=0):
    return Article(title=title, link=link, published=_dt(hours_ago), source=source, category="Tech")


def _config(preferred_sources=None, threshold=0.85):
    return AppConfig(
        feeds=FeedConfig(opml_file="feedly_rss.opml", timeout_seconds=10, skip_feedly_proxy=True),
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
        llm=LLMConfig(base_url="http://localhost:11434", embedding_model="nomic-embed-text", dedup_threshold=threshold),
        deduplication=DeduplicationConfig(preferred_sources=preferred_sources or []),
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


def test_ut_004_3_handle_all_unique():
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    deduped = _dedup_by_exact_url(articles)

    assert len(deduped) == 2


def test_ut_005_1_cluster_similar_titles(monkeypatch):
    articles = [
        _article("Apple releases iOS 18", "https://example.com/1", hours_ago=1),
        _article("Apple releases iOS 18 today", "https://example.com/2", hours_ago=2),
    ]

    def fake_embedding(*args, **kwargs):
        text = kwargs["text"] if "text" in kwargs else args[2]
        if "today" in text:
            return [0.999, 0.001]
        return [1.0, 0.0]

    monkeypatch.setattr("src.deduplicator._get_embedding", fake_embedding)

    deduped = deduplicate_articles(articles, _config())

    assert len(deduped) == 1


def test_ut_005_2_keep_different_titles(monkeypatch):
    articles = [
        _article("Apple news", "https://example.com/1", hours_ago=1),
        _article("Fed rates", "https://example.com/2", hours_ago=2),
    ]

    vectors = {
        "Apple news": [1.0, 0.0],
        "Fed rates": [0.0, 1.0],
    }

    def fake_embedding(*args, **kwargs):
        text = kwargs.get("text")
        if text is None and len(args) > 2:
            text = args[2]
        return vectors[text]

    monkeypatch.setattr("src.deduplicator._get_embedding", fake_embedding)

    deduped = deduplicate_articles(articles, _config())

    assert len(deduped) == 2


def test_ut_005_3_prefer_preferred_source(monkeypatch):
    articles = [
        _article("Market update", "https://example.com/1", source="Reuters", hours_ago=3),
        _article("Market update", "https://example.com/2", source="Other", hours_ago=1),
    ]

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: [1.0, 0.0])

    deduped = deduplicate_articles(articles, _config(preferred_sources=["Reuters"]))

    assert len(deduped) == 1
    assert deduped[0].source == "Reuters"


def test_ut_005_4_prefer_recent_if_no_preferred(monkeypatch):
    older = _article("Cluster", "https://example.com/1", source="A", hours_ago=3)
    newer = _article("Cluster", "https://example.com/2", source="B", hours_ago=1)

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: [1.0, 0.0])

    deduped = deduplicate_articles([older, newer], _config(preferred_sources=[]))

    assert len(deduped) == 1
    assert deduped[0].link == newer.link


def test_ut_005_5_handle_ollama_timeout(monkeypatch):
    articles = [_article("a", "https://example.com/1", hours_ago=3), _article("b", "https://example.com/2", hours_ago=1)]

    def raise_timeout(*args, **kwargs):
        raise TimeoutError("ollama timeout")

    monkeypatch.setattr("src.deduplicator._get_embedding", raise_timeout)

    with pytest.raises(DeduplicationError):
        deduplicate_articles(articles, _config())


def test_ut_005_6_handle_empty_list():
    deduped = deduplicate_articles([], _config())

    assert deduped == []


def test_ut_005_7_on_dedup_failure_fail(monkeypatch):
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("down")))

    cfg = _config()

    with pytest.raises(DeduplicationError):
        deduplicate_articles(articles, cfg)


def test_ut_005_8_model_not_found(monkeypatch):
    articles = [_article("a", "https://example.com/1"), _article("b", "https://example.com/2")]

    mock_response = MagicMock()
    mock_response.status_code = 404

    def raise_404(*args, **kwargs):
        exc = requests.exceptions.HTTPError(response=mock_response)
        exc.response = mock_response
        raise exc

    monkeypatch.setattr("src.deduplicator._get_embedding", raise_404)

    with pytest.raises(DeduplicationError):
        deduplicate_articles(articles, _config())
