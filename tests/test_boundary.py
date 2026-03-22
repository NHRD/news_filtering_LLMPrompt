"""Boundary Condition Tests (BC) for the RSS news filtering pipeline."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

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
from src.main import run_pipeline
from src.rss_fetcher import FeedSource
from src.time_filter import filter_recent_articles


def _config(tmp_path):
    return AppConfig(
        feeds=FeedConfig(opml_file=str(tmp_path / "feeds.opml"), timeout_seconds=1, skip_feedly_proxy=True),
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
        gemini=GeminiConfig(model="gemini-2.0-flash", dedup_batch_size=80),
        deduplication=DeduplicationConfig(preferred_sources=["Reuters"], on_dedup_failure="send_anyway"),
        email=EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="secret",
            recipients=["to@example.com"],
            max_articles_per_email=200,
        ),
        output=OutputConfig(
            save_html=True,
            html_dir=str(tmp_path / "output"),
            log_file=str(tmp_path / "logs/news.log"),
            state_file=str(tmp_path / "state/last_run.json"),
        ),
        system=SystemConfig(poweroff_after_run=False),
    )


def test_bc_001_empty_feed_pipeline_completes(monkeypatch, tmp_path):
    """BC-001: 全フィードが空（0件）の場合でもパイプラインが正常終了すること。"""
    cfg = _config(tmp_path)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr("src.main.fetch_articles", lambda *args, **kwargs: [])

    rc = run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert rc == 0


def test_bc_005_mixed_timezone_articles_normalized_to_utc(monkeypatch):
    """BC-005: UTC/JST/EST 混在のタイムゾーンを持つ記事が UTC 基準で正しく比較されること。"""
    # base_time: UTC 基準のカットオフ時刻
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    # now_utc を固定してカットオフ計算を安定させる
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)

    # time_window_hours=6 → cutoff = base_time - 6h = 2026-02-17 06:00 UTC
    # Articles:
    #   UTC article:  2026-02-17 07:00 UTC  → cutoff より後 → 通過すべき
    #   JST article:  2026-02-17 16:30 JST (+09:00) = 2026-02-17 07:30 UTC → cutoff より後 → 通過すべき
    #   EST article:  2026-02-17 00:30 EST (-05:00) = 2026-02-17 05:30 UTC → cutoff より前 → 除外されるべき

    utc_tz = timezone.utc
    jst_tz = timezone(timedelta(hours=9))
    est_tz = timezone(timedelta(hours=-5))

    article_utc = Article(
        title="UTC Article",
        link="https://example.com/utc",
        published=datetime(2026, 2, 17, 7, 0, tzinfo=utc_tz),
        source="Reuters",
        category="Tech",
    )
    article_jst = Article(
        title="JST Article",
        link="https://example.com/jst",
        published=datetime(2026, 2, 17, 16, 30, tzinfo=jst_tz),  # = 07:30 UTC
        source="NHK",
        category="Tech",
    )
    article_est = Article(
        title="EST Article",
        link="https://example.com/est",
        published=datetime(2026, 2, 17, 0, 30, tzinfo=est_tz),  # = 05:30 UTC
        source="CNN",
        category="Tech",
    )

    articles = [article_utc, article_jst, article_est]

    filtered, cutoff = filter_recent_articles(
        articles=articles,
        time_window_hours=6,
        last_run=None,
        force=True,
    )

    # cutoff は base_time - 6h = 06:00 UTC
    assert cutoff == datetime(2026, 2, 17, 6, 0, tzinfo=timezone.utc)

    # UTC と JST の記事は cutoff 以降 → 通過
    # EST の記事は cutoff より前 → 除外
    assert len(filtered) == 2

    filtered_titles = {a.title for a in filtered}
    assert "UTC Article" in filtered_titles
    assert "JST Article" in filtered_titles
    assert "EST Article" not in filtered_titles
