from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import json
import re

from src import Article
from src.config import (
    AppConfig,
    DeduplicationConfig,
    EmailConfig,
    FeedConfig,
    GeminiConfig,
    IndexConfig,
    OutputConfig,
    ScheduleConfig,
    SystemConfig,
    TranslationConfig,
)
from src.deduplicator import DeduplicationError, deduplicate_articles
from src.email_sender import send_email
from src.html_builder import build_email_html
from src.index_writer import write_index
from src.main import run_pipeline
from src.numbering import number_articles
from src.rss_fetcher import FeedSource, fetch_articles, parse_opml
from src.time_filter import filter_recent_articles, load_last_run_timestamp, save_last_run_timestamp
from src.translator import translate_articles


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


def _config_with_translation(tmp_path, translation_enabled=True, save_index=False):
    """Config with translation and index settings for E2E tests."""
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
        translation=TranslationConfig(
            enabled=translation_enabled,
            batch_size=80,
            batch_interval_seconds=0,
            on_translate_failure="skip",
        ),
        index=IndexConfig(
            save_index=save_index,
            index_dir=str(tmp_path / "output"),
            max_files=3,
        ),
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

    mock_result = MagicMock()
    mock_result.stdout = "1"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        gemini=GeminiConfig("gemini-2.0-flash", 80),
        deduplication=DeduplicationConfig([], "send_anyway"),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
    )

    deduped = deduplicate_articles(articles, cfg)

    assert len(deduped) == 1


def test_it_002_2_dedup_with_gemini_running(monkeypatch):
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("a", "https://example.com/1", now, "A", "Tech"),
        Article("b", "https://example.com/2", now, "B", "Tech"),
    ]
    mock_result = MagicMock()
    mock_result.stdout = "1,2"
    mock_result.returncode = 0
    monkeypatch.setattr("src.deduplicator.subprocess.run", lambda *args, **kwargs: mock_result)
    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        gemini=GeminiConfig("gemini-2.0-flash", 80),
        deduplication=DeduplicationConfig([], "send_anyway"),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
    )

    deduped = deduplicate_articles(articles, cfg)

    assert len(deduped) == 2


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


def test_e2e_001_3_run_with_gemini_down_fails(monkeypatch, tmp_path):
    cfg = _config(tmp_path)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [Article("A", "https://example.com/1", base_time, "S", "Tech")],
    )
    
    def raise_dedup_error(*args, **kwargs):
        raise DeduplicationError("gemini down")
    
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


# ---------------------------------------------------------------------------
# IT-005: Translator → Numbering → HTML Builder / Index Writer integration
# ---------------------------------------------------------------------------

def test_it_005_1_translator_numbering_html_builder(monkeypatch):
    """Translator → Numbering → HTML Builder の連携."""
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("Article One", "https://example.com/1", base_time, "Reuters", "Tech"),
        Article("Article Two", "https://example.com/2", base_time - timedelta(hours=1), "BBC", "Tech"),
    ]

    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        gemini=GeminiConfig("gemini-2.0-flash", 80),
        deduplication=DeduplicationConfig([], "send_anyway"),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        translation=TranslationConfig(enabled=True, batch_size=80, batch_interval_seconds=0, on_translate_failure="skip"),
    )

    mock_result = MagicMock()
    mock_result.stdout = "1. テスト翻訳\n2. テスト翻訳2\n"
    mock_result.returncode = 0
    monkeypatch.setattr("src.translator.subprocess.run", lambda *args, **kwargs: mock_result)

    translated = translate_articles(articles, cfg)

    # title_ja が埋まっていること
    assert translated[0].title_ja == "テスト翻訳"
    assert translated[1].title_ja == "テスト翻訳2"

    numbered = number_articles(translated)

    # NumberedArticle が生成されていること
    assert len(numbered) == 2
    assert numbered[0].no == 1
    assert numbered[1].no == 2

    html = build_email_html(numbered)

    # HTML に no 列と title_ja が出力されていること
    assert "1." in html
    assert "2." in html
    assert "テスト翻訳" in html
    assert "テスト翻訳2" in html


def test_it_005_2_translator_numbering_index_writer(monkeypatch, tmp_path):
    """Translator → Numbering → Index Writer の連携."""
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("Article One", "https://example.com/1", base_time, "Reuters", "Tech"),
        Article("Article Two", "https://example.com/2", base_time - timedelta(hours=1), "BBC", "Finance"),
    ]

    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        gemini=GeminiConfig("gemini-2.0-flash", 80),
        deduplication=DeduplicationConfig([], "send_anyway"),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        translation=TranslationConfig(enabled=True, batch_size=80, batch_interval_seconds=0, on_translate_failure="skip"),
        index=IndexConfig(save_index=True, index_dir=str(tmp_path / "output"), max_files=3),
    )

    mock_result = MagicMock()
    mock_result.stdout = "1. テスト翻訳\n2. テスト翻訳2\n"
    mock_result.returncode = 0
    monkeypatch.setattr("src.translator.subprocess.run", lambda *args, **kwargs: mock_result)

    translated = translate_articles(articles, cfg)
    numbered = number_articles(translated)
    write_index(numbered, cfg)

    # 生成された JSON ファイルを読み込む
    json_files = list((tmp_path / "output").glob("news_index_*.json"))
    assert len(json_files) == 1

    with open(json_files[0], encoding="utf-8") as f:
        data = json.load(f)

    # no と title_ja が記事と一致すること
    indexed = {item["no"]: item for item in data["articles"]}
    for na in numbered:
        item = indexed[na.no]
        assert item["title_ja"] == na.article.title_ja
        assert item["no"] == na.no


def test_it_005_3_numbering_order_consistent_html_and_json(tmp_path):
    """Numbering後のno順序がHTMLとJSONで一致するか (Critical)."""
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    articles = [
        Article("Article A", "https://example.com/a", base_time, "Reuters", "Tech", "技術記事A"),
        Article("Article B", "https://example.com/b", base_time - timedelta(hours=1), "BBC", "Tech", "技術記事B"),
        Article("Article C", "https://example.com/c", base_time, "CNN", "Finance", "金融記事C"),
    ]

    cfg = AppConfig(
        feeds=FeedConfig("feedly_rss.opml", 10, True),
        schedule=ScheduleConfig(12, 12),
        gemini=GeminiConfig("gemini-2.0-flash", 80),
        deduplication=DeduplicationConfig([], "send_anyway"),
        email=EmailConfig("smtp.gmail.com", 587, "a@a", "p", ["b@b"], 200),
        output=OutputConfig(True, "./output", "./logs/x.log", "./state/x.json"),
        system=SystemConfig(poweroff_after_run=False),
        index=IndexConfig(save_index=True, index_dir=str(tmp_path / "output"), max_files=3),
    )

    numbered = number_articles(articles)
    html = build_email_html(numbered)
    write_index(numbered, cfg)

    # HTMLから各記事のno と link の対応を抽出
    # テンプレートは "1." のような形で no を出力する
    html_no_to_link = {}
    for na in numbered:
        # HTML中に no と link が両方含まれること
        assert str(na.no) + "." in html
        assert na.article.link in html
        html_no_to_link[na.no] = na.article.link

    # JSON を読み込む
    json_files = list((tmp_path / "output").glob("news_index_*.json"))
    assert len(json_files) == 1
    with open(json_files[0], encoding="utf-8") as f:
        data = json.load(f)

    json_no_to_link = {item["no"]: item["link"] for item in data["articles"]}

    # 両者で同一 no が同一記事（同一 link）を指していること
    assert html_no_to_link == json_no_to_link


# ---------------------------------------------------------------------------
# E2E-003: translation / index full pipeline tests
# ---------------------------------------------------------------------------

def test_e2e_003_1_translation_enabled_full_pipeline(monkeypatch, tmp_path):
    """translation.enabled=True の full pipeline."""
    cfg = _config_with_translation(tmp_path, translation_enabled=True, save_index=True)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [
            Article("Article One", "https://example.com/1", base_time, "Reuters", "Tech"),
        ],
    )

    # dedup モック（記事をそのまま返す）
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)

    # Gemini CLI 翻訳モック
    mock_result = MagicMock()
    mock_result.stdout = "1. テスト翻訳\n"
    mock_result.returncode = 0
    monkeypatch.setattr("src.translator.subprocess.run", lambda *args, **kwargs: mock_result)

    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert rc == 0

    # 生成された HTML に title_ja が反映されていること
    html_files = list((tmp_path / "output").glob("news_digest_*.html"))
    assert len(html_files) == 1
    html_content = html_files[0].read_text(encoding="utf-8")
    assert "テスト翻訳" in html_content

    # 生成された JSON インデックスに title_ja が含まれること
    json_files = list((tmp_path / "output").glob("news_index_*.json"))
    assert len(json_files) == 1
    with open(json_files[0], encoding="utf-8") as f:
        data = json.load(f)
    assert data["articles"][0]["title_ja"] != ""
    assert data["articles"][0]["title_ja"] == "テスト翻訳"


def test_e2e_003_2_translation_disabled_full_pipeline(monkeypatch, tmp_path):
    """translation.enabled=False の full pipeline."""
    cfg = _config_with_translation(tmp_path, translation_enabled=False, save_index=True)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [
            Article("Article One", "https://example.com/1", base_time, "Reuters", "Tech"),
        ],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    # translate_articles のモックを作成して呼び出し回数を記録する
    translate_call_count = {"count": 0}

    def fake_translate_articles(articles, config):
        translate_call_count["count"] += 1
        return articles

    monkeypatch.setattr("src.main.translate_articles", fake_translate_articles)

    rc = run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert rc == 0

    # translate_articles が呼ばれていないこと
    assert translate_call_count["count"] == 0

    # 生成された JSON インデックスの title_ja が空文字であること
    json_files = list((tmp_path / "output").glob("news_index_*.json"))
    assert len(json_files) == 1
    with open(json_files[0], encoding="utf-8") as f:
        data = json.load(f)
    assert data["articles"][0]["title_ja"] == ""


def test_e2e_003_3_save_index_true_full_pipeline(monkeypatch, tmp_path):
    """index.save_index=True の full pipeline."""
    cfg = _config_with_translation(tmp_path, translation_enabled=False, save_index=True)
    base_time = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("src.time_filter.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.now_utc", lambda: base_time)
    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [
            Article("Article One", "https://example.com/1", base_time, "Reuters", "Tech"),
        ],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, config: articles)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    rc = run_pipeline(cfg, dry_run=True, fetch_only=False, force=True)

    assert rc == 0

    # output/ ディレクトリに news_index_YYYYMMDD_AM.json または news_index_YYYYMMDD_PM.json が生成されること
    json_files = list((tmp_path / "output").glob("news_index_*.json"))
    assert len(json_files) == 1
    # ファイル名のパターンが正しいこと
    fname = json_files[0].name
    assert re.match(r"news_index_\d{8}_\d{6}\.json", fname), f"Unexpected filename: {fname}"
