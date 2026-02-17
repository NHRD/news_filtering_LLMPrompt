#!/usr/bin/env python3
"""Fetch 100 newest news titles and links from Feedly OPML RSS feeds."""

import socket
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

import feedparser

OPML_FILE = "feedly-ca53bc95-9ca8-4579-a877-542cfb958671-2026-02-17.opml"
OUTPUT_FILE = "news_list.txt"
FEEDLY_PROXY_PREFIX = "https://feedly.com/web/"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
SOCKET_TIMEOUT = 10
TARGET_COUNT = 100


def parse_opml(opml_path: str) -> List[Dict[str, str]]:
    tree = ET.parse(opml_path)
    root = tree.getroot()

    seen_urls = set()
    feeds = []

    for outline in root.iter("outline"):
        if outline.get("type") != "rss":
            continue
        xml_url = outline.get("xmlUrl", "")
        if not xml_url:
            continue
        if xml_url.startswith(FEEDLY_PROXY_PREFIX):
            print(f"[SKIP] Feedly proxy: {outline.get('text', 'Unknown')}")
            continue
        if xml_url in seen_urls:
            continue
        seen_urls.add(xml_url)
        feeds.append({"url": xml_url, "name": outline.get("text", "Unknown")})

    return feeds


def fetch_articles(feeds: List[Dict[str, str]]) -> List[Dict]:
    socket.setdefaulttimeout(SOCKET_TIMEOUT)
    all_articles = []
    total = len(feeds)

    for i, feed in enumerate(feeds, 1):
        print(f"[{i}/{total}] Fetching: {feed['name']}...")
        try:
            parsed = feedparser.parse(feed["url"], request_headers=REQUEST_HEADERS)
            for entry in parsed.entries:
                pub_date = entry.get("published_parsed") or entry.get("updated_parsed")
                all_articles.append({
                    "title": entry.get("title", "(No title)"),
                    "link": entry.get("link", "(No link)"),
                    "date": pub_date,
                })
        except Exception as e:
            print(f"[WARN] Failed to fetch: {feed['name']} ({feed['url']}): {e}")

    return all_articles


def sort_and_select(articles: List[Dict], count: int) -> List[Dict]:
    def sort_key(article):
        d = article["date"]
        if d is None:
            return (0, 0, 0, 0, 0, 0)
        return tuple(d[:6])

    articles.sort(key=sort_key, reverse=True)
    return articles[:count]


def output_results(articles: List[Dict], output_path: str):
    lines = []
    for i, article in enumerate(articles, 1):
        lines.append(f"{i}. {article['title']}")
        lines.append(f"   {article['link']}")
        lines.append("")

    text = "\n".join(lines)
    print(text)

    Path(output_path).write_text(text, encoding="utf-8")
    print(f"Saved to {output_path}")


def main():
    if not Path(OPML_FILE).exists():
        print(f"Error: {OPML_FILE} not found. Export it from https://feedly.com/i/opml")
        raise SystemExit(1)

    feeds = parse_opml(OPML_FILE)
    if not feeds:
        print("No feeds found in OPML file.")
        raise SystemExit(1)
    print(f"Found {len(feeds)} unique feeds.\n")

    articles = fetch_articles(feeds)
    if not articles:
        print("No articles found across all feeds.")
        raise SystemExit(1)
    print(f"\nCollected {len(articles)} articles total.\n")

    top = sort_and_select(articles, TARGET_COUNT)
    output_results(top, OUTPUT_FILE)


if __name__ == "__main__":
    main()
