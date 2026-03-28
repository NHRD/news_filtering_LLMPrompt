"""Unit tests for src/translator.py (UT-009)."""

import subprocess
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch

import pytest

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
from src.translator import TranslationError, translate_articles


def _make_article(title: str, category: str = "Tech", n: int = 0) -> Article:
    base = datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc)
    return Article(
        title=title,
        link=f"https://example.com/{n}",
        published=base,
        source="TestSource",
        category=category,
    )


def _make_config(
    enabled: bool = True,
    batch_size: int = 80,
    on_translate_failure: str = "skip",
) -> AppConfig:
    """Build a minimal AppConfig for translation tests."""
    return AppConfig(
        feeds=FeedConfig(opml_file="dummy.opml", timeout_seconds=10, skip_feedly_proxy=True),
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
        gemini=GeminiConfig(model="gemini-2.0-flash", dedup_batch_size=80),
        deduplication=DeduplicationConfig(preferred_sources=[], on_dedup_failure="send_anyway"),
        email=EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="a@a.com",
            sender_password="pass",
            recipients=["b@b.com"],
            max_articles_per_email=200,
        ),
        output=OutputConfig(
            save_html=True,
            html_dir="./output",
            log_file="./logs/news.log",
            state_file="./state/last_run.json",
        ),
        system=SystemConfig(poweroff_after_run=False),
        translation=TranslationConfig(
            enabled=enabled,
            batch_size=batch_size,
            batch_interval_seconds=15,
            on_translate_failure=on_translate_failure,
        ),
        index=IndexConfig(save_index=True, index_dir="./output", max_files=3),
    )


def _mock_run(stdout: str, returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    if returncode != 0:
        result.check_returncode.side_effect = subprocess.CalledProcessError(returncode, "gemini")
    else:
        result.check_returncode.return_value = None
    return result


# UT-009-1: 正常翻訳（全件）
def test_ut_009_1_translate_all_success():
    articles = [_make_article("Fed hikes rates", n=1), _make_article("Apple unveils chip", n=2)]
    stdout = "1. 連邦準備制度、利上げ\n2. Appleが新チップを発表"
    config = _make_config()

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "連邦準備制度、利上げ"
    assert result[1].title_ja == "Appleが新チップを発表"
    assert result[0].title == "Fed hikes rates"
    assert result[1].title == "Apple unveils chip"


# UT-009-2: バッチ分割（batch_size超過時）
def test_ut_009_2_batch_split():
    articles = [_make_article(f"Article {i}", n=i) for i in range(5)]
    # batch_size=3 → 2バッチに分割される
    config = _make_config(batch_size=3)
    call_count = {"n": 0}

    def fake_run(*args, **kwargs):
        call_count["n"] += 1
        batch_idx = call_count["n"]
        if batch_idx == 1:
            # バッチ1: 記事0,1,2 → ローカル番号1,2,3
            stdout = "1. 記事0\n2. 記事1\n3. 記事2"
        else:
            # バッチ2: 記事3,4 → ローカル番号1,2
            stdout = "1. 記事3\n2. 記事4"
        return _mock_run(stdout)

    with patch("subprocess.run", side_effect=fake_run):
        result = translate_articles(articles, config)

    assert call_count["n"] == 2
    assert result[0].title_ja == "記事0"
    assert result[2].title_ja == "記事2"
    assert result[3].title_ja == "記事3"
    assert result[4].title_ja == "記事4"


# UT-009-3: 個別行パース失敗 → フォールバック（original title使用）
def test_ut_009_3_individual_line_parse_failure_fallback():
    articles = [_make_article("Title A", n=1), _make_article("Title B", n=2)]
    # 1行目のみ正常、2行目は番号なしフォーマット
    stdout = "1. タイトルA\n翻訳テキストだけ"
    config = _make_config()

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "タイトルA"
    assert result[1].title_ja == "Title B"  # フォールバック: original title


# UT-009-4: 範囲外番号 → フォールバック
def test_ut_009_4_out_of_range_number_fallback():
    articles = [_make_article("Title A", n=1)]
    # N=99 は範囲外
    stdout = "1. タイトルA\n99. 存在しない番号"
    config = _make_config()

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "タイトルA"
    assert len(result) == 1


# UT-009-5: 重複番号 → 後出し優先
def test_ut_009_5_duplicate_number_last_wins():
    articles = [_make_article("Title A", n=1), _make_article("Title B", n=2)]
    # N=1 が2回出現 → 後出しを採用
    stdout = "1. 最初の翻訳\n2. タイトルB翻訳\n1. 後出しの翻訳"
    config = _make_config()

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "後出しの翻訳"
    assert result[1].title_ja == "タイトルB翻訳"


# UT-009-6: 全行パース失敗 + on_translate_failure=skip → original title使用
def test_ut_009_6_all_parse_fail_skip():
    articles = [_make_article("Title A", n=1), _make_article("Title B", n=2)]
    # パース不能な出力
    stdout = "翻訳できませんでした\nエラーが発生しました"
    config = _make_config(on_translate_failure="skip")

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "Title A"
    assert result[1].title_ja == "Title B"


# UT-009-7: 全行パース失敗 + on_translate_failure=fail → TranslationError raise
def test_ut_009_7_all_parse_fail_fail_mode():
    articles = [_make_article("Title A", n=1)]
    stdout = "パース不能な出力"
    config = _make_config(on_translate_failure="fail")

    with patch("subprocess.run", return_value=_mock_run(stdout)):
        with pytest.raises(TranslationError):
            translate_articles(articles, config)


# UT-009-8: Gemini CLI エラー（非ゼロ終了） + on_translate_failure=skip → original title使用
def test_ut_009_8_gemini_cli_error_skip():
    articles = [_make_article("Title A", n=1), _make_article("Title B", n=2)]
    config = _make_config(on_translate_failure="skip")

    with patch("subprocess.run", return_value=_mock_run("", returncode=1)):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "Title A"
    assert result[1].title_ja == "Title B"


# UT-009-9: Gemini CLI 未起動/例外 + on_translate_failure=skip → original title使用
def test_ut_009_9_gemini_cli_exception_skip():
    articles = [_make_article("Title A", n=1)]
    config = _make_config(on_translate_failure="skip")

    with patch("subprocess.run", side_effect=FileNotFoundError("gemini not found")):
        result = translate_articles(articles, config)

    assert result[0].title_ja == "Title A"


# UT-009-10: translation.enabled=False → main.py 側でスキップ（translate_articles 未呼び出し）
# NOTE: enabled チェックは main.py に実装されている。
# このテストは main.py のルーティングロジックを検証する（translate_articles 自体ではなく）。
def test_ut_009_10_translation_disabled_in_pipeline(monkeypatch):
    """translation.enabled=False の場合、run_pipeline が translate_articles を呼ばない。"""
    from src.main import run_pipeline
    from src.rss_fetcher import FeedSource

    base_time = datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc)
    config = _make_config(enabled=False)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [_make_article("Title A", n=1)._replace(published=base_time)],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, cfg: articles)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    translate_called = {"called": False}

    def fake_translate(articles, cfg):
        translate_called["called"] = True
        return articles

    monkeypatch.setattr("src.main.translate_articles", fake_translate)
    monkeypatch.setattr("src.main.write_index", lambda *args, **kwargs: None)

    rc = run_pipeline(config, dry_run=True, fetch_only=False, force=True)

    assert rc == 0
    assert translate_called["called"] is False


# UT-009-11: 空リスト → 空リストを返す
def test_ut_009_11_empty_list():
    config = _make_config()

    with patch("subprocess.run") as mock_run:
        result = translate_articles([], config)
        mock_run.assert_not_called()

    assert result == []
