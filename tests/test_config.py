import textwrap

import pytest

from src.config import load_config


def _base_yaml(sender="${GMAIL_ADDRESS}", password="${GMAIL_APP_PASSWORD}"):
    return textwrap.dedent(
        f"""
        feeds:
          opml_file: feedly_rss.opml
          timeout_seconds: 10
          skip_feedly_proxy: true
        schedule:
          interval_hours: 24
          time_window_hours: 24
        gemini:
          model: gemini-2.0-flash
          dedup_batch_size: 80
        deduplication:
          preferred_sources: [Reuters]
          on_dedup_failure: send_anyway
        email:
          smtp_server: smtp.gmail.com
          smtp_port: 587
          sender_email: {sender}
          sender_password: {password}
          recipients: [to@example.com]
          max_articles_per_email: 200
        output:
          save_html: true
          html_dir: ./output
          log_file: ./logs/news_filter.log
          state_file: ./state/last_run.json
        """
    )


def test_ut_008_1_load_config_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(_base_yaml(), encoding="utf-8")

    cfg = load_config(str(cfg_file))

    assert cfg.email.sender_email == "sender@example.com"
    assert cfg.schedule.time_window_hours == 24
    assert cfg.gemini.model == "gemini-2.0-flash"


def test_ut_008_2_expand_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "env-sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "env-pass")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(_base_yaml(), encoding="utf-8")

    cfg = load_config(str(cfg_file))

    assert cfg.email.sender_email == "env-sender@example.com"
    assert cfg.email.sender_password == "env-pass"


def test_ut_008_3_handle_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("does_not_exist_config.yaml")


def test_ut_008_4_handle_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("UNDEFINED_ENV", raising=False)
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(_base_yaml(sender="${UNDEFINED_ENV}"), encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(str(cfg_file))


def test_ut_008_5_preferred_sources_loading(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(_base_yaml(), encoding="utf-8")

    cfg = load_config(str(cfg_file))

    assert "Reuters" in cfg.deduplication.preferred_sources
    assert cfg.deduplication.on_dedup_failure == "send_anyway"
