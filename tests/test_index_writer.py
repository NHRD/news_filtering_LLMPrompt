"""Unit tests for src/index_writer.py (UT-011)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from unittest.mock import patch

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
from src.index_writer import write_index
from src.numbering import NumberedArticle


def _make_numbered_article(
    no: int,
    title: str = "Title",
    title_ja: str = "タイトル",
    category: str = "Tech",
    hours_offset: int = 0,
) -> NumberedArticle:
    pub = datetime(2026, 3, 11, 8 + hours_offset, 0, tzinfo=timezone.utc)
    article = Article(
        title=title,
        link=f"https://example.com/{no}",
        published=pub,
        source="Reuters",
        category=category,
        title_ja=title_ja,
    )
    return NumberedArticle(no=no, article=article)


def _make_config(tmp_path: Path, save_index: bool = True, max_files: int = 3) -> AppConfig:
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
            html_dir=str(tmp_path / "output"),
            log_file=str(tmp_path / "logs/news.log"),
            state_file=str(tmp_path / "state/last_run.json"),
        ),
        system=SystemConfig(poweroff_after_run=False),
        translation=TranslationConfig(enabled=True, batch_size=80, batch_interval_seconds=0, on_translate_failure="skip"),
        index=IndexConfig(
            save_index=save_index,
            index_dir=str(tmp_path),
            max_files=max_files,
        ),
    )


# UT-011-1: 正常書き込み（AMセッション）
def test_ut_011_1_write_am_session(tmp_path: Path):
    numbered = [_make_numbered_article(1, "Fed hikes", "連邦準備利上げ")]
    config = _make_config(tmp_path)
    # hour=8 → AM
    fixed_time = datetime(2026, 3, 11, 8, 0, 48)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 8, 0, 48, tzinfo=timezone.utc)]
        write_index(numbered, config)

    files = list(tmp_path.glob("news_index_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["session"] == "AM"


# UT-011-2: 正常書き込み（PMセッション）
def test_ut_011_2_write_pm_session(tmp_path: Path):
    numbered = [_make_numbered_article(1, "Market close", "市場終値")]
    config = _make_config(tmp_path)
    # hour=20 → PM
    fixed_time = datetime(2026, 3, 11, 20, 0, 48)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 20, 0, 48, tzinfo=timezone.utc)]
        write_index(numbered, config)

    files = list(tmp_path.glob("news_index_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["session"] == "PM"


# UT-011-3: JSONフォーマット検証（全フィールド存在確認）
def test_ut_011_3_json_schema_all_fields(tmp_path: Path):
    numbered = [_make_numbered_article(1, "Fed hikes rates", "連邦準備利上げ", "Finance")]
    config = _make_config(tmp_path)
    fixed_time = datetime(2026, 3, 11, 8, 0, 0)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 8, 0, 0, tzinfo=timezone.utc)]
        write_index(numbered, config)

    files = list(tmp_path.glob("news_index_*.json"))
    data = json.loads(files[0].read_text(encoding="utf-8"))

    # トップレベルフィールド
    assert "session" in data
    assert "run_time" in data
    assert "article_count" in data
    assert "articles" in data

    # 記事フィールド
    article = data["articles"][0]
    assert "no" in article
    assert "title_ja" in article
    assert "title_en" in article
    assert "link" in article
    assert "source" in article
    assert "category" in article
    assert "published" in article

    assert article["no"] == 1
    assert article["title_en"] == "Fed hikes rates"
    assert article["title_ja"] == "連邦準備利上げ"
    assert article["category"] == "Finance"
    assert data["article_count"] == 1


# UT-011-4: FIFO: max_files=3で4件目書き込み時に最古が削除される
def test_ut_011_4_fifo_max_files(tmp_path: Path):
    existing_files = [
        tmp_path / "news_index_20260309_080000.json",
        tmp_path / "news_index_20260309_200000.json",
        tmp_path / "news_index_20260310_080000.json",
    ]
    for f in existing_files:
        f.write_text('{"session":"AM"}', encoding="utf-8")

    numbered = [_make_numbered_article(1)]
    config = _make_config(tmp_path, max_files=3)
    fixed_time = datetime(2026, 3, 10, 20, 0, 0)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [
            fixed_time,
            datetime(2026, 3, 10, 20, 0, 0, tzinfo=timezone.utc),
        ]
        write_index(numbered, config)

    remaining = sorted(tmp_path.glob("news_index_*.json"))
    names = [f.name for f in remaining]

    assert len(remaining) == 3
    assert "news_index_20260309_080000.json" not in names
    assert "news_index_20260309_200000.json" in names
    assert "news_index_20260310_080000.json" in names
    assert "news_index_20260310_200000.json" in names


# UT-011-5: FIFO: ファイル名の HHMMSS 辞書順が時系列順と一致するか
def test_ut_011_5_fifo_hhmmss_lexicographic_order_matches_chronology(tmp_path: Path):
    filenames = [
        "news_index_20260309_080000.json",
        "news_index_20260309_200000.json",
        "news_index_20260310_080000.json",
    ]
    for name in filenames:
        (tmp_path / name).write_text("{}", encoding="utf-8")

    files = sorted(tmp_path.glob("news_index_*.json"))
    names = [f.name for f in files]

    assert names == [
        "news_index_20260309_080000.json",
        "news_index_20260309_200000.json",
        "news_index_20260310_080000.json",
    ]
    assert names[0] < names[1]
    assert names[1] < names[2]


# UT-011-6: ディレクトリ自動作成（os.makedirs を使う実装を確認）
def test_ut_011_6_auto_create_directory(tmp_path: Path):
    """index_writer.py は os.makedirs(index_dir, exist_ok=True) を持つため自動作成される。"""
    new_dir = tmp_path / "new_subdir"
    assert not new_dir.exists()

    config = _make_config(tmp_path)
    # index_dir を存在しないサブディレクトリに変更
    config = config._replace(
        index=IndexConfig(save_index=True, index_dir=str(new_dir), max_files=3)
    )
    numbered = [_make_numbered_article(1)]
    fixed_time = datetime(2026, 3, 11, 8, 0, 0)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 8, 0, 0, tzinfo=timezone.utc)]
        write_index(numbered, config)

    assert new_dir.exists()
    files = list(new_dir.glob("news_index_*.json"))
    assert len(files) == 1


# UT-011-7: save_index=False → main.py 側でスキップ（write_index 未呼び出し）
# NOTE: save_index チェックは main.py に実装されている。
# このテストは main.py のルーティングロジックを検証する。
def test_ut_011_7_save_index_false_skips_write(tmp_path: Path, monkeypatch):
    """save_index=False の場合、run_pipeline が write_index を呼ばない。"""
    from datetime import timezone as tz_module

    from src.main import run_pipeline
    from src.rss_fetcher import FeedSource

    base_time = datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc)
    config = _make_config(tmp_path, save_index=False)

    monkeypatch.setattr("src.main.parse_opml", lambda *args, **kwargs: [FeedSource("u", "n", "Tech")])
    monkeypatch.setattr(
        "src.main.fetch_articles",
        lambda *args, **kwargs: [
            Article("Title A", "https://example.com/1", base_time, "Reuters", "Tech", "タイトルA")
        ],
    )
    monkeypatch.setattr("src.main.deduplicate_articles", lambda articles, cfg: articles)
    monkeypatch.setattr("src.main.translate_articles", lambda articles, cfg: articles)
    monkeypatch.setattr("src.main.send_email", lambda *args, **kwargs: True)

    write_called = {"called": False}

    def fake_write_index(numbered, cfg):
        write_called["called"] = True

    monkeypatch.setattr("src.main.write_index", fake_write_index)

    rc = run_pipeline(config, dry_run=True, fetch_only=False, force=True)

    assert rc == 0
    assert write_called["called"] is False


# UT-011-8: I/Oエラー → パイプライン継続（例外を吐かない）
def test_ut_011_8_io_error_does_not_raise(tmp_path: Path):
    """write_index が I/O エラーを外に伝播しないこと。"""
    numbered = [_make_numbered_article(1)]

    # 存在しないディレクトリでも makedirs が呼ばれるが、
    # ここでは makedirs 自体を失敗させて OSError を発生させる
    config = _make_config(tmp_path)

    import builtins

    original_open = builtins.open

    def fail_open(path, *args, **kwargs):
        if "news_index_" in str(path):
            raise OSError("Simulated I/O error")
        return original_open(path, *args, **kwargs)

    fixed_time = datetime(2026, 3, 11, 8, 0, 0)
    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 8, 0, 0, tzinfo=timezone.utc)]
        with patch("builtins.open", side_effect=fail_open):
            try:
                write_index(numbered, config)
            except Exception as exc:
                pytest.fail(f"write_index should not raise, but raised: {exc}")


# UT-011-9: 複数記事の article_count が正しい
def test_ut_011_9_article_count_correct(tmp_path: Path):
    numbered = [_make_numbered_article(i + 1, f"Title {i}") for i in range(5)]
    config = _make_config(tmp_path)
    fixed_time = datetime(2026, 3, 11, 8, 0, 0)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [fixed_time, datetime(2026, 3, 11, 8, 0, 0, tzinfo=timezone.utc)]
        write_index(numbered, config)

    files = list(tmp_path.glob("news_index_*.json"))
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["article_count"] == 5
    assert len(data["articles"]) == 5


def test_ut_011_10_same_second_rerun_overwrites_file(tmp_path: Path):
    first_numbered = [_make_numbered_article(1, "First run", "初回実行")]
    second_numbered = [
        _make_numbered_article(1, "Second run 1", "再実行1"),
        _make_numbered_article(2, "Second run 2", "再実行2"),
    ]
    config = _make_config(tmp_path)

    fixed_time = datetime(2026, 3, 11, 8, 0, 5)
    fixed_time_utc = datetime(2026, 3, 11, 8, 0, 5, tzinfo=timezone.utc)

    with patch("src.index_writer.datetime") as mock_dt:
        mock_dt.now.side_effect = [
            fixed_time,
            fixed_time_utc,
            fixed_time,
            fixed_time_utc,
        ]
        write_index(first_numbered, config)
        write_index(second_numbered, config)

    files = list(tmp_path.glob("news_index_*.json"))
    assert len(files) == 1

    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["article_count"] == 2
    assert len(data["articles"]) == 2
    assert data["articles"][0]["title_en"] == "Second run 1"
    assert data["articles"][1]["title_en"] == "Second run 2"
