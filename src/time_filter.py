"""Time filtering and run-state persistence."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from . import Article
except ImportError:  # pragma: no cover
    from __init__ import Article


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso8601_timestamp(ts: str) -> datetime:
    """Parse ISO-8601 timestamp with timezone in Python 3.6+."""
    normalized = ts.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if len(normalized) >= 6 and normalized[-6] in "+-" and normalized[-3] == ":":
        normalized = normalized[:-3] + normalized[-2:]

    formats = (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    )
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    raise ValueError("Invalid ISO-8601 timestamp: {0}".format(ts))


def load_last_run_timestamp(state_file: str) -> Optional[datetime]:
    path = Path(state_file)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("last_successful_run")
        if not ts:
            return None
        dt = _parse_iso8601_timestamp(ts)
        if dt.tzinfo is None:
            logging.warning("[Time Filter] Naive last_run timestamp assumed UTC")
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        logging.warning("[Time Filter] Failed to load state file: %s", exc)
        return None


def save_last_run_timestamp(state_file: str, timestamp: Optional[datetime] = None) -> None:
    path = Path(state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = (timestamp or now_utc()).astimezone(timezone.utc).isoformat()
    payload = {"last_successful_run": ts}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def compute_cutoff(time_window_hours: int, last_run: Optional[datetime], force: bool = False) -> datetime:
    default_cutoff = now_utc() - timedelta(hours=time_window_hours)
    if force or last_run is None:
        return default_cutoff
    return max(last_run, default_cutoff)


def filter_recent_articles(
    articles: List[Article],
    time_window_hours: int,
    last_run: Optional[datetime],
    force: bool = False,
) -> Tuple[List[Article], datetime]:
    cutoff = compute_cutoff(time_window_hours=time_window_hours, last_run=last_run, force=force)
    filtered = []
    for article in articles:
        if article.published is None:
            logging.warning("[Time Filter] Skipping article without date: %s", article.title)
            continue
        pub = article.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
            logging.warning("[Time Filter] Assuming UTC for naive datetime: %s", article.title)
        if pub >= cutoff:
            filtered.append(article)
    logging.info("[Time Filter] %s articles within cutoff %s", len(filtered), cutoff.isoformat())
    return filtered, cutoff
