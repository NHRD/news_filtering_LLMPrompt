from datetime import datetime, timezone

import pytest

from src import Article
from src.rss_fetcher import FeedSource, fetch_articles, parse_opml


def _write_opml(path, body_xml):
    path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<opml version=\"1.0\">
  <body>
%s
  </body>
</opml>
"""
        % body_xml,
        encoding="utf-8",
    )


def test_ut_001_1_parse_valid_opml(tmp_path):
    opml = tmp_path / "feeds.opml"
    _write_opml(
        opml,
        """
    <outline text=\"Tech\" title=\"Tech\">
      <outline type=\"rss\" text=\"Feed A\" xmlUrl=\"https://example.com/a.xml\"/>
    </outline>
    """,
    )

    feeds = parse_opml(str(opml))

    assert feeds == [FeedSource(url="https://example.com/a.xml", name="Feed A", category="Tech")]


def test_ut_001_2_skip_feedly_proxy_urls(tmp_path):
    opml = tmp_path / "feeds.opml"
    _write_opml(
        opml,
        """
    <outline text=\"Root\">
      <outline type=\"rss\" text=\"Proxy\" xmlUrl=\"https://feedly.com/web/i/subscription/feed%2Fexample\"/>
      <outline type=\"rss\" text=\"Direct\" xmlUrl=\"https://example.com/feed.xml\"/>
    </outline>
    """,
    )

    feeds = parse_opml(str(opml), skip_feedly_proxy=True)

    assert [f.url for f in feeds] == ["https://example.com/feed.xml"]


def test_ut_001_3_handle_duplicate_feed_urls(tmp_path):
    opml = tmp_path / "feeds.opml"
    _write_opml(
        opml,
        """
    <outline text=\"Root\">
      <outline type=\"rss\" text=\"A\" xmlUrl=\"https://example.com/feed.xml\"/>
      <outline type=\"rss\" text=\"B\" xmlUrl=\"https://example.com/feed.xml\"/>
    </outline>
    """,
    )

    feeds = parse_opml(str(opml))

    assert len(feeds) == 1
    assert feeds[0].url == "https://example.com/feed.xml"


def test_ut_001_4_handle_empty_opml(tmp_path):
    opml = tmp_path / "empty.opml"
    opml.write_text("<opml version='1.0'></opml>", encoding="utf-8")

    feeds = parse_opml(str(opml))

    assert feeds == []


def test_ut_001_5_handle_malformed_opml(tmp_path):
    opml = tmp_path / "bad.opml"
    opml.write_text("<opml><body><outline>", encoding="utf-8")

    with pytest.raises(Exception):
        parse_opml(str(opml))


def test_ut_002_1_fetch_valid_rss_feed(monkeypatch):
    feeds = [FeedSource(url="https://example.com/rss", name="TechCrunch", category="Tech")]

    class Parsed:
        entries = [
            {
                "title": "Article",
                "link": "https://example.com/1",
                "published": "Tue, 13 Feb 2024 10:00:00 GMT",
            }
        ]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    articles = fetch_articles(feeds)

    assert len(articles) == 1
    assert isinstance(articles[0], Article)


def test_ut_002_2_handle_feed_timeout(monkeypatch, caplog):
    feeds = [FeedSource(url="https://example.com/rss", name="TimeoutFeed", category="Tech")]

    def _raise(*args, **kwargs):
        raise TimeoutError("timeout")

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", _raise)

    articles = fetch_articles(feeds)

    assert articles == []
    assert "Failed to fetch" in caplog.text


def test_ut_002_3_handle_malformed_feed(monkeypatch, caplog):
    feeds = [FeedSource(url="https://example.com/rss", name="BadFeed", category="Tech")]

    class Parsed:
        entries = [{"title": "bad", "link": "https://example.com/1", "published": "not-a-date"}]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    articles = fetch_articles(feeds)

    assert articles == []
    assert "Invalid date" in caplog.text


def test_ut_002_4_extract_article_metadata(monkeypatch):
    feeds = [FeedSource(url="https://example.com/rss", name="Reuters", category="Finance")]

    class Parsed:
        entries = [
            {
                "title": "Fed update",
                "link": "https://example.com/fed",
                "published": "Tue, 13 Feb 2024 10:00:00 GMT",
            }
        ]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    articles = fetch_articles(feeds)

    assert len(articles) == 1
    a = articles[0]
    assert a.title == "Fed update"
    assert a.link == "https://example.com/fed"
    assert a.source == "Reuters"
    assert a.category == "Finance"
    assert a.published == datetime(2024, 2, 13, 10, 0, tzinfo=timezone.utc)


def test_ut_002_5_handle_missing_date(monkeypatch, caplog):
    feeds = [FeedSource(url="https://example.com/rss", name="NoDateFeed", category="Tech")]

    class Parsed:
        entries = [{"title": "No Date", "link": "https://example.com/no-date"}]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    articles = fetch_articles(feeds)

    # Articles without a valid date are excluded by the implementation
    assert len(articles) == 0
    assert "Skip article without valid published_date" in caplog.text


def test_ut_002_6_handle_naive_date_string(monkeypatch, caplog):
    feeds = [FeedSource(url="https://example.com/rss", name="NaiveDateFeed", category="Tech")]

    class Parsed:
        entries = [
            {
                "title": "Naive",
                "link": "https://example.com/naive",
                # No timezone info (GMT/UTC)
                "published": "Tue, 13 Feb 2024 10:00:00",
            }
        ]

    monkeypatch.setattr("src.rss_fetcher.feedparser.parse", lambda *args, **kwargs: Parsed())

    articles = fetch_articles(feeds)

    assert len(articles) == 1
    assert articles[0].published == datetime(2024, 2, 13, 10, 0, tzinfo=timezone.utc)
    assert "Naive date string assumed UTC" in caplog.text
