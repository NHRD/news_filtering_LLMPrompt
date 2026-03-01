from datetime import datetime, timedelta, timezone

from src import Article
from src.config import (
    AppConfig,
    DeduplicationConfig,
    EmailConfig,
    FeedConfig,
    LLMConfig,
    MailFetchConfig,
    MailingListEntry,
    OutputConfig,
    ScheduleConfig,
    SystemConfig,
)
from src.deduplicator import DeduplicationError, deduplicate_articles
from src.email_sender import send_email
from src.html_builder import build_email_html
from src.main import run_pipeline
from src.rss_fetcher import FeedSource, fetch_articles, parse_opml
from src.time_filter import filter_recent_articles, load_last_run_timestamp, save_last_run_timestamp


def _config(tmp_path):
    return AppConfig(
        feeds=FeedConfig(opml_file=str(tmp_path / "feeds.opml"), timeout_seconds=1, skip_feedly_proxy=True),
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
        llm=LLMConfig(base_url="http://localhost:11434", embedding_model="nomic-embed-text", dedup_threshold=0.85),
        deduplication=DeduplicationConfig(preferred_sources=["Reuters"]),
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
        mail_fetch=MailFetchConfig(enabled=False, imap_server="imap.gmail.com", imap_port=993, imap_user="", imap_password="", timeout_seconds=30, lists=[]),
    )


def _config_mail_enabled(tmp_path):
    cfg = _config(tmp_path)
    return cfg._replace(
        mail_fetch=MailFetchConfig(
            enabled=True,
            imap_server="imap.gmail.com",
            imap_port=993,
            imap_user="sender@example.com",
            imap_password="secret",
            timeout_seconds=30,
            lists=[
                MailingListEntry(
                    name="Example List",
                    category="Mailing Lists",
                    label="example-list",
                )
            ],
        )
    )


def test_it_001_1_fetch_real_like_and_filter_by_time(tmp_path, monkeypatch):
    fixed_now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: fixed_now)

    opml = tmp_path / "feeds.opml"
    opml.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<opml version=\"1.0\"><body>
  <outline text=\"Tech\"><outline type=\"rss\" text=\"Feed\" xmlUrl=\"https://example.com/rss\"/></outline>
</body></opml>""",
        encoding="utf-8",
    )

    class Parsed:
        entries = [
            {"title": "new", "link": "https://example.com/1", "published": "Tue, 17 Feb 2026 10:00:00 GMT"},
            {"title": "old", "link": "https://example.com/2", "published": "Sun, 15 Feb 2026 10:00:00 GMT"},
        ]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    feeds = parse_opml(str(opml))
    fetched = fetch_articles(feeds)
    filtered, _ = filter_recent_articles(
        fetched,
        time_window_hours=24,
        last_run=datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc),
    )

    assert len(filtered) == 1
    assert filtered[0].title == "new"


def test_it_001_2_state_persistence_across_runs(tmp_path):
    state_file = tmp_path / "state" / "last_run.json"
    ts = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    save_last_run_timestamp(str(state_file), ts)
    loaded = load_last_run_timestamp(str(state_file))

    assert loaded == ts


def test_it_002_1_filter_then_deduplicate(monkeypatch):
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("same", "https://example.com/1", now, "A", "Tech"),
        Article("same", "https://example.com/1", now - timedelta(hours=1), "A", "Tech"),
    ]

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: [1.0, 0.0])
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        llm=LLMConfig("http://localhost:11434", "nomic-embed-text", 0.85),
        deduplication=DeduplicationConfig([]),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        mail_fetch=MailFetchConfig(enabled=False, imap_server="imap.gmail.com", imap_port=993, imap_user="", imap_password="", timeout_seconds=30, lists=[]),
    )

    deduped = deduplicate_articles(articles, cfg)

    assert len(deduped) == 1


def test_it_002_2_dedup_with_ollama_running(monkeypatch):
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("a", "https://example.com/1", now, "A", "Tech"),
        Article("b", "https://example.com/2", now, "B", "Tech"),
    ]
    calls = {"count": 0}

    def fake_embedding(*args, **kwargs):
        calls["count"] += 1
        return [1.0, 0.0] if calls["count"] == 1 else [0.0, 1.0]

    monkeypatch.setattr("src.deduplicator._get_embedding", fake_embedding)
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        llm=LLMConfig("http://localhost:11434", "nomic-embed-text", 0.85),
        deduplication=DeduplicationConfig([]),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        mail_fetch=MailFetchConfig(enabled=False, imap_server="imap.gmail.com", imap_port=993, imap_user="", imap_password="", timeout_seconds=30, lists=[]),
    )

    deduplicate_articles(articles, cfg)

    assert calls["count"] == 2


def test_it_003_1_build_html_from_deduped_articles():
    articles = [
        Article("A", "https://example.com/1", datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc), "Reuters", "Finance")
    ]

    html = build_email_html(articles)

    assert "Reuters" in html
    assert "Finance" in html


def test_it_004_1_build_and_send_mocked_smtp(monkeypatch):
    html = build_email_html(
        [Article("A", "https://example.com/1", datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc), "Reuters", "Finance")]
    )

    sent = {"ok": False}

    def fake_send(config, subject, html_body):
        sent["ok"] = True
        return True

    # Patch the module-level reference so the imported send_email is replaced
    import src.email_sender
    monkeypatch.setattr(src.email_sender, "send_email", fake_send)

    cfg = EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200)
    ok = src.email_sender.send_email(cfg, "Subj", html)

    assert ok is True


def test_e2e_001_1_run_pipeline_dry_run(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    send_called = {"count": 0}
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: send_called.__setitem__("count", send_called["count"] + 1))

    rc = run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert rc == 0
    assert send_called["count"] == 0
    assert len(list((tmp_path / "output").glob("news_digest_*.html"))) == 1


def test_e2e_001_2_run_pipeline_full_with_mocked_email(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    sent = {"called": False}

    def fake_send(*args, **kwargs):
        sent["called"] = True
        return True

    monkeypatch.setattr("src.main.send_email", fake_send)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0
    assert sent["called"] is True


def test_e2e_001_3_run_with_ollama_down_fails(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    
    def raise_dedup_error(*args, **kwargs):
        raise DeduplicationError("ollama down")
    
    monkeypatch.setattr("src.main.deduplicate_articles", raise_dedup_error)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 1


def test_e2e_002_1_dry_run_flag(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    sent = {"called": False}
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: sent.__setitem__("called", True))

    run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert sent["called"] is False


def test_e2e_002_2_fetch_only_flag(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    dedup_called = {"called": False}
    monkeypatch.setattr("src.main.deduplicate_articles", lambda *args, **kwargs: dedup_called.__setitem__("called", True))

    rc = run_pipeline(cfg, dry_run=False, fetch_only=True, force=True)

    assert rc == 0
    assert dedup_called["called"] is False


def test_e2e_002_3_force_flag(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time - timedelta(hours=20), "S", "Tech")],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0


def test_it_005_1_merge_rss_and_mail_in_pipeline(monkeypatch, tmp_path):
    cfg = _config_mail_enabled(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    rss_article = Article("RSS A", "https://example.com/rss-a", base_time, "RSS", "Tech")
    mail_article = Article("Mail A", "", base_time, "ML", "Mailing Lists", "Body Content")
    captured = {"titles": []}

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr("src.main.fetch_articles", lambda *args, **kwargs: [rss_article])
    monkeypatch.setattr("src.main.fetch_mail_articles", lambda *args, **kwargs: [mail_article])
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr(
        "src.main.deduplicate_articles",
        lambda articles, config: captured.__setitem__("titles", [a.title for a in articles]) or articles,
    )
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0
    assert set(captured["titles"]) == {"RSS A", "Mail A"}


def test_it_005_2_time_filter_applies_to_rss_and_mail(monkeypatch, tmp_path):
    cfg = _config_mail_enabled(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    rss_article = Article("RSS New", "https://example.com/rss-new", base_time, "RSS", "Tech")
    old_mail = Article(
        "Mail Old",
        "",
        base_time - timedelta(hours=30),
        "ML",
        "Mailing Lists",
        "Body",
    )
    captured = {"titles": []}

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr("src.main.fetch_articles", lambda *args, **kwargs: [rss_article])
    monkeypatch.setattr("src.main.fetch_mail_articles", lambda *args, **kwargs: [old_mail])
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr(
        "src.main.deduplicate_articles",
        lambda articles, config: captured.__setitem__("titles", [a.title for a in articles]) or articles,
    )
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0
    assert captured["titles"] == ["RSS New"]


def test_it_005_3_dedup_exact_url_between_rss_and_mail(monkeypatch):
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("RSS item", "https://example.com/shared", now, "RSS", "Tech"),
        Article("Mail item", "", now - timedelta(minutes=10), "ML", "Mailing Lists", "Body"),
        Article("Other", "https://example.com/other", now, "RSS", "Tech"),
    ]
    vectors = {
        "RSS item": [1.0, 0.0, 0.0],
        "Other": [0.0, 1.0, 0.0],
        "Mail item": [0.0, 0.0, 1.0],
    }
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(24, 24),
        llm=LLMConfig("http://localhost:11434", "nomic-embed-text", 0.95),
        deduplication=DeduplicationConfig([]),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        mail_fetch=MailFetchConfig(False, "imap.gmail.com", 993, "", "", 30, []),
    )

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: vectors[kwargs["text"]])
    deduped = deduplicate_articles(articles, cfg)

    assert len(deduped) == 3


def test_it_005_4_dedup_title_similarity_between_rss_and_mail(monkeypatch):
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("Linux kernel 6.10 released", "https://example.com/rss-1", now, "RSS", "Tech"),
        Article("Linux kernel 6.10 release", "", now - timedelta(minutes=1), "ML", "Mailing Lists", "Body"),
    ]
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(24, 24),
        llm=LLMConfig("http://localhost:11434", "nomic-embed-text", 0.8),
        deduplication=DeduplicationConfig([]),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        mail_fetch=MailFetchConfig(False, "imap.gmail.com", 993, "", "", 30, []),
    )

    monkeypatch.setattr("src.deduplicator._get_embedding", lambda *args, **kwargs: [1.0, 0.0, 0.0])
    deduped = deduplicate_articles(articles, cfg)

    assert len(deduped) == 1


def test_e2e_001_4_run_pipeline_with_rss_and_mail(monkeypatch, tmp_path):
    cfg = _config_mail_enabled(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    rss_article = Article("RSS A", "https://example.com/rss-a", base_time, "RSS", "Tech")
    mail_article = Article("Mail A", "", base_time, "ML", "Mailing Lists", "Special Body Content")
    sent = {"subject": "", "html": ""}

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr("src.main.fetch_articles", lambda *args, **kwargs: [rss_article])
    monkeypatch.setattr("src.main.fetch_mail_articles", lambda *args, **kwargs: [mail_article])
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)

    def fake_send(_cfg, subject, html):
        sent["subject"] = subject
        sent["html"] = html
        return True

    monkeypatch.setattr("src.main.send_email", fake_send)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0
    assert "2 articles" in sent["subject"]
    assert "RSS A" in sent["html"]
    assert "Mail A" in sent["html"]
    assert "Special Body Content" in sent["html"]


def test_e2e_001_5_imap_failure_graceful_degradation(monkeypatch, tmp_path):
    cfg = _config_mail_enabled(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    rss_article = Article("RSS only", "https://example.com/rss-only", base_time, "RSS", "Tech")
    captured = {"titles": []}

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr("src.main.fetch_articles", lambda *args, **kwargs: [rss_article])
    monkeypatch.setattr("src.main.fetch_mail_articles", lambda *args, **kwargs: [])
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr(
        "src.main.deduplicate_articles",
        lambda articles, config: captured.__setitem__("titles", [a.title for a in articles]) or articles,
    )
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=False, fetch_only=False, force=True)

    assert rc == 0
    assert captured["titles"] == ["RSS only"]
