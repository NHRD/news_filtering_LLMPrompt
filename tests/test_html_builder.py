from datetime import datetime, timedelta, timezone

from src import Article
from src.html_builder import build_email_html


def _article(title, category="Tech", hours_ago=0):
    base = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    return Article(
        title=title,
        link=f"https://example.com/{title.replace(' ', '-')}".lower(),
        published=base - timedelta(hours=hours_ago),
        source="Source",
        category=category,
    )


def test_ut_006_1_generate_valid_html():
    html = build_email_html([_article("Hello")])

    assert "<!DOCTYPE html>" in html
    assert "<html>" in html
    assert "News Digest" in html


def test_ut_006_2_group_by_category():
    html = build_email_html([_article("A", "Tech"), _article("B", "Finance")])

    assert "Tech" in html
    assert "Finance" in html


def test_ut_006_3_sort_by_date():
    html = build_email_html([_article("Older", "Tech", hours_ago=5), _article("Newer", "Tech", hours_ago=1)])

    assert html.index("Newer") < html.index("Older")


def test_ut_006_4_escape_html_in_title():
    html = build_email_html([_article("<script>alert(1)</script>")])

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_ut_006_5_handle_empty_list():
    html = build_email_html([])

    assert "No articles" in html


def test_ut_006_6_respect_max_articles():
    articles = [_article(f"Article {i}") for i in range(300)]

    html = build_email_html(articles)

    assert html.count('class="article"') == 200
