"""Configuration loader for RSS news filtering."""

import os
import re
from pathlib import Path
from typing import Any, List, NamedTuple

import yaml
from dotenv import load_dotenv


_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


class FeedConfig(NamedTuple):
    opml_file: str
    timeout_seconds: int
    skip_feedly_proxy: bool


class ScheduleConfig(NamedTuple):
    interval_hours: int
    time_window_hours: int


class GeminiConfig(NamedTuple):
    model: str
    dedup_batch_size: int


class DeduplicationConfig(NamedTuple):
    preferred_sources: List[str]
    on_dedup_failure: str


class EmailConfig(NamedTuple):
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipients: List[str]
    max_articles_per_email: int


class OutputConfig(NamedTuple):
    save_html: bool
    html_dir: str
    log_file: str
    state_file: str


class SystemConfig(NamedTuple):
    poweroff_after_run: bool


class TranslationConfig(NamedTuple):
    enabled: bool
    batch_size: int
    on_translate_failure: str


class IndexConfig(NamedTuple):
    save_index: bool
    index_dir: str
    max_files: int


_DEFAULT_TRANSLATION = TranslationConfig(enabled=True, batch_size=80, on_translate_failure="skip")
_DEFAULT_INDEX = IndexConfig(save_index=True, index_dir="./output", max_files=3)


class AppConfig(NamedTuple):
    feeds: FeedConfig
    schedule: ScheduleConfig
    gemini: GeminiConfig
    deduplication: DeduplicationConfig
    email: EmailConfig
    output: OutputConfig
    system: SystemConfig
    translation: TranslationConfig = _DEFAULT_TRANSLATION
    index: IndexConfig = _DEFAULT_INDEX


def _resolve_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    if isinstance(value, str):
        match = _ENV_PATTERN.match(value.strip())
        if match:
            return os.getenv(match.group(1), "")
    return value


def _require(value: str, field_name: str) -> str:
    if not value:
        raise ValueError(f"Missing required config value: {field_name}")
    return value


def load_config(path: str = "config.yaml") -> AppConfig:
    load_dotenv()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg = _resolve_env(raw)

    feeds = cfg.get("feeds", {})
    schedule = cfg.get("schedule", {})
    gemini = cfg.get("gemini", {})
    dedup = cfg.get("deduplication", {})
    email = cfg.get("email", {})
    output = cfg.get("output", {})
    system = cfg.get("system", {})
    translation = cfg.get("translation", {})
    index = cfg.get("index", {})

    return AppConfig(
        feeds=FeedConfig(
            opml_file=feeds.get("opml_file", "default_rss.opml"),
            timeout_seconds=int(feeds.get("timeout_seconds", 10)),
            skip_feedly_proxy=bool(feeds.get("skip_feedly_proxy", True)),
        ),
        schedule=ScheduleConfig(
            interval_hours=int(schedule.get("interval_hours", 24)),
            time_window_hours=int(schedule.get("time_window_hours", 24)),
        ),
        gemini=GeminiConfig(
            model=gemini.get("model", "gemini-2.0-flash"),
            dedup_batch_size=int(gemini.get("dedup_batch_size", 80)),
        ),
        deduplication=DeduplicationConfig(
            preferred_sources=list(dedup.get("preferred_sources", [])),
            on_dedup_failure=dedup.get("on_dedup_failure", "send_anyway"),
        ),
        email=EmailConfig(
            smtp_server=email.get("smtp_server", "smtp.gmail.com"),
            smtp_port=int(email.get("smtp_port", 587)),
            sender_email=_require(email.get("sender_email", ""), "email.sender_email"),
            sender_password=_require(email.get("sender_password", ""), "email.sender_password"),
            recipients=[r for r in email.get("recipients", []) if r],
            max_articles_per_email=int(email.get("max_articles_per_email", 200)),
        ),
        output=OutputConfig(
            save_html=bool(output.get("save_html", True)),
            html_dir=output.get("html_dir", "./output"),
            log_file=output.get("log_file", "./logs/news_filter.log"),
            state_file=output.get("state_file", "./state/last_run.json"),
        ),
        system=SystemConfig(
            poweroff_after_run=bool(system.get("poweroff_after_run", False)),
        ),
        translation=TranslationConfig(
            enabled=bool(translation.get("enabled", True)),
            batch_size=int(translation.get("batch_size", 80)),
            on_translate_failure=translation.get("on_translate_failure", "skip"),
        ),
        index=IndexConfig(
            save_index=bool(index.get("save_index", True)),
            index_dir=index.get("index_dir", "./output"),
            max_files=int(index.get("max_files", 3)),
        ),
    )
