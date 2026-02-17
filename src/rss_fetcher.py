"""RSS fetching and OPML parsing."""

import logging
import socket
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, NamedTuple, Optional, Set

import feedparser

try:
    from . import Article
except ImportError:  # pragma: no cover
    from __init__ import Article

FEEDLY_PROXY_PREFIX = "https://feedly.com/web/"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}


class FeedSource(NamedTuple):
    url: str
    name: str
    category: str


def parse_opml(opml_path: str, skip_feedly_proxy: bool = True) -> List[FeedSource]:
    tree = ET.parse(opml_path)
    root = tree.getroot()

    feeds = []  # type: List[FeedSource]
    seen_urls = set()  # type: Set[str]

    body = root.find("body")
    if body is None:
        return feeds

    for node in body:
        _collect_feeds(node, default_category=node.attrib.get("text", "Uncategorized"), out=feeds)

    filtered = []  # type: List[FeedSource]
    for feed in feeds:
        if skip_feedly_proxy and feed.url.startswith(FEEDLY_PROXY_PREFIX):
            logging.info("[RSS Fetcher] Skip Feedly proxy: %s", feed.url)
            continue
        if feed.url in seen_urls:
            continue
        seen_urls.add(feed.url)
        filtered.append(feed)

    return filtered


def _collect_feeds(node: ET.Element, default_category: str, out: List[FeedSource]) -> None:
    node_type = node.attrib.get("type")
    text = node.attrib.get("text") or node.attrib.get("title") or "Unknown"

    if node_type == "rss":
        url = node.attrib.get("xmlUrl", "").strip()
        if not url:
            return
        out.append(FeedSource(url=url, name=text, category=default_category or "Uncategorized"))
        return

    category = text or default_category
    for child in list(node):
        _collect_feeds(child, category, out)


def _to_datetime_utc(entry: Dict[str, Any], source_name: str) -> Optional[datetime]:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is not None:
        # feedparser time struct has no timezone; architecture requires assuming UTC.
        logging.warning("[RSS Fetcher] Naive published_parsed assumed UTC: %s", source_name)
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    for key in ("published", "updated"):
        text = entry.get(key)
        if not text:
            continue
        try:
            dt = parsedate_to_datetime(text)
            if dt.tzinfo is None:
                logging.warning("[RSS Fetcher] Naive date string assumed UTC: %s", source_name)
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            logging.warning("[RSS Fetcher] Invalid date on %s: %s", source_name, text)

    return None


def fetch_articles(feeds: List[FeedSource], timeout_seconds: int = 10) -> List[Article]:
    socket.setdefaulttimeout(timeout_seconds)
    all_articles = []  # type: List[Article]

    for idx, feed in enumerate(feeds, start=1):
        logging.info("[RSS Fetcher] [%s/%s] Fetching: %s", idx, len(feeds), feed.name)
        try:
            parsed = feedparser.parse(feed.url, request_headers=REQUEST_HEADERS)
        except Exception as exc:  # pragma: no cover
            logging.warning("[RSS Fetcher] Failed to fetch %s: %s", feed.url, exc)
            continue

        for entry in parsed.entries:
            published = _to_datetime_utc(entry, feed.name)
            if published is None:
                logging.warning("[RSS Fetcher] Skip article without valid published_date: %s", feed.name)
                continue

            title = (entry.get("title") or "(No title)").strip()
            link = (entry.get("link") or "").strip()
            if not link:
                continue

            all_articles.append(
                Article(
                    title=title,
                    link=link,
                    published=published,
                    source=feed.name,
                    category=feed.category,
                )
            )

    return all_articles
