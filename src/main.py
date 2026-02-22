"""Entry point for RSS News Filtering pipeline."""

import argparse
import logging
from datetime import timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    from .config import AppConfig, load_config
    from .deduplicator import deduplicate_articles
    from .email_sender import send_email
    from .html_builder import build_email_html
    from .rss_fetcher import fetch_articles, parse_opml
    from .time_filter import (
        filter_recent_articles,
        load_last_run_timestamp,
        now_utc,
        save_last_run_timestamp,
    )
except ImportError:  # pragma: no cover
    from config import AppConfig, load_config
    from deduplicator import deduplicate_articles
    from email_sender import send_email
    from html_builder import build_email_html
    from rss_fetcher import fetch_articles, parse_opml
    from time_filter import (
        filter_recent_articles,
        load_last_run_timestamp,
        now_utc,
        save_last_run_timestamp,
    )


def _setup_logging(log_file: str) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            ),
        ],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RSS News Filtering")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without sending email")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch and filter only")
    parser.add_argument("--force", action="store_true", help="Ignore last_run state cutoff")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    return parser.parse_args()


def _write_html_if_needed(config: AppConfig, html: str) -> None:
    if not config.output.save_html:
        return
    out_dir = Path(config.output.html_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"news_digest_{now_utc().strftime('%Y%m%d_%H%M%S')}.html"
    out_file.write_text(html, encoding="utf-8")
    logging.info("[HTML Builder] Saved HTML to %s", out_file)


def run_pipeline(config, dry_run=False, fetch_only=False, force=False):
    # type: (AppConfig, bool, bool, bool) -> int
    logging.info("[Main] Starting fetch cycle")

    feeds = parse_opml(config.feeds.opml_file, skip_feedly_proxy=config.feeds.skip_feedly_proxy)
    logging.info("[RSS Fetcher] Found %s unique feeds in OPML", len(feeds))

    articles = fetch_articles(feeds, timeout_seconds=config.feeds.timeout_seconds)
    logging.info("[RSS Fetcher] Fetched %s articles", len(articles))
    if not articles:
        logging.info("[Main] No articles fetched")
        return 0

    last_run = load_last_run_timestamp(config.output.state_file)
    recent_articles, cutoff = filter_recent_articles(
        articles=articles,
        time_window_hours=config.schedule.time_window_hours,
        last_run=last_run,
        force=force,
    )
    logging.info("[Main] Cutoff used: %s", cutoff.isoformat())

    if fetch_only:
        logging.info("[Main] Fetch-only mode completed")
        save_last_run_timestamp(config.output.state_file, now_utc())
        return 0

    deduped = deduplicate_articles(recent_articles, config)
    logging.info("[Deduplicator] Reduced to %s unique articles", len(deduped))

    capped = deduped[: config.email.max_articles_per_email]
    if len(capped) < len(deduped):
        logging.info(
            "[Main] Applied max_articles_per_email=%s (%s -> %s)",
            config.email.max_articles_per_email,
            len(deduped),
            len(capped),
        )

    html = build_email_html(capped)
    logging.info("[HTML Builder] Generated email (%s bytes)", len(html.encode("utf-8")))
    _write_html_if_needed(config, html)

    window_start = cutoff.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    window_end = now_utc().astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"News Digest | {len(capped)} articles | {window_start} - {window_end}"

    if dry_run:
        logging.info("[Main] Dry-run mode: email not sent")
    else:
        if not capped:
            logging.info("[Main] No articles to send")
        else:
            send_email(config.email, subject, html)

    save_last_run_timestamp(config.output.state_file, now_utc())
    logging.info("[Main] Cycle completed successfully")
    return 0


def main():
    # type: () -> int
    args = _parse_args()
    config = load_config(args.config)
    _setup_logging(config.output.log_file)
    return run_pipeline(config, dry_run=args.dry_run, fetch_only=args.fetch_only, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
