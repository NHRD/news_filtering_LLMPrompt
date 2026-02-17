from datetime import datetime, timedelta, timezone

from src import Article
from src.time_filter import compute_cutoff, filter_recent_articles


FIXED_NOW = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)


def _article(title, published):
    return Article(title=title, link=f"https://example.com/{title}", published=published, source="Source", category="Tech")


def test_ut_003_1_filter_recent_articles(monkeypatch):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    articles = [
        _article("a", FIXED_NOW - timedelta(hours=1)),
        _article("b", FIXED_NOW - timedelta(hours=5, minutes=59)),
    ]

    filtered, _ = filter_recent_articles(articles, time_window_hours=6, last_run=None)

    assert len(filtered) == 2


def test_ut_003_2_filter_old_articles(monkeypatch):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    articles = [_article("a", FIXED_NOW - timedelta(hours=24))]

    filtered, _ = filter_recent_articles(articles, time_window_hours=6, last_run=None)

    assert filtered == []


def test_ut_003_3_handle_timezone_aware_dates(monkeypatch):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    jst = timezone(timedelta(hours=9))
    articles = [_article("aware", datetime(2026, 2, 17, 19, 0, tzinfo=jst))]

    filtered, _ = filter_recent_articles(articles, time_window_hours=6, last_run=None)

    assert len(filtered) == 1


def test_ut_003_4_handle_timezone_naive_dates(monkeypatch, caplog):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    articles = [_article("naive", datetime(2026, 2, 17, 10, 0))]

    filtered, _ = filter_recent_articles(articles, time_window_hours=6, last_run=None)

    assert len(filtered) == 1
    assert "assumed UTC" in caplog.text


def test_ut_003_5_handle_none_date(monkeypatch, caplog):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    articles = [_article("none", None)]  # type: ignore[arg-type]

    filtered, _ = filter_recent_articles(articles, time_window_hours=6, last_run=None)

    assert filtered == []
    assert "None" in caplog.text or "missing" in caplog.text.lower()


def test_ut_003_6_use_last_run_for_recovery(monkeypatch):
    monkeypatch.setattr("src.time_filter.now_utc", lambda: FIXED_NOW)
    last_run = FIXED_NOW - timedelta(hours=2)

    cutoff = compute_cutoff(time_window_hours=12, last_run=last_run, force=False)

    assert cutoff == last_run
