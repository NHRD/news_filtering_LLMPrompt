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


class LLMConfig(NamedTuple):
    base_url: str
    embedding_model: str
    dedup_threshold: float


class DeduplicationConfig(NamedTuple):
    preferred_sources: List[str]


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


class MailingListEntry(NamedTuple):
    name: str      # Article.source に使用
    category: str  # Article.category に使用 (HTML グルーピング用)
    label: str     # Gmail ラベル名


class MailFetchConfig(NamedTuple):
    enabled: bool
    imap_server: str
    imap_port: int
    imap_user: str      # GMAIL_ADDRESS から取得
    imap_password: str  # GMAIL_APP_PASSWORD から取得
    timeout_seconds: int
    lists: List[MailingListEntry]


class AppConfig(NamedTuple):
    feeds: FeedConfig
    schedule: ScheduleConfig
    llm: LLMConfig
    deduplication: DeduplicationConfig
    email: EmailConfig
    output: OutputConfig
    system: SystemConfig
    mail_fetch: MailFetchConfig


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
    llm = cfg.get("llm", {})
    dedup = cfg.get("deduplication", {})
    email = cfg.get("email", {})
    output = cfg.get("output", {})
    system = cfg.get("system", {})
    mail_raw = cfg.get("mailing_lists", {})

    sender_email = _require(email.get("sender_email", ""), "email.sender_email")
    sender_password = _require(email.get("sender_password", ""), "email.sender_password")

    mail_lists = []
    for entry in mail_raw.get("lists", []):
        mail_lists.append(MailingListEntry(
            name=entry.get("name", ""),
            category=entry.get("category", "Mailing Lists"),
            label=entry.get("label", ""),
        ))

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
        llm=LLMConfig(
            base_url=_require(llm.get("base_url", "http://localhost:11434"), "llm.base_url"),
            embedding_model=llm.get("embedding_model", "nomic-embed-text"),
            dedup_threshold=float(llm.get("dedup_threshold", 0.85)),
        ),
        deduplication=DeduplicationConfig(
            preferred_sources=list(dedup.get("preferred_sources", [])),
        ),
        email=EmailConfig(
            smtp_server=email.get("smtp_server", "smtp.gmail.com"),
            smtp_port=int(email.get("smtp_port", 587)),
            sender_email=sender_email,
            sender_password=sender_password,
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
        mail_fetch=MailFetchConfig(
            enabled=bool(mail_raw.get("enabled", False)),
            imap_server=mail_raw.get("imap_server", "imap.gmail.com"),
            imap_port=int(mail_raw.get("imap_port", 993)),
            imap_user=sender_email,
            imap_password=sender_password,
            timeout_seconds=int(mail_raw.get("timeout_seconds", 30)),
            lists=mail_lists,
        ),
    )
