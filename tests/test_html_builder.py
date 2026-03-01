from datetime import datetime, timedelta, timezone

from src import Article
from src.html_builder import build_email_html


def _article(title, category="Tech", hours_ago=0, link=None, body=""):
    base = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    return Article(
        title=title,
        link=link if link is not None else f"https://example.com/{title.replace(' ', '-')}".lower(),
        published=base - timedelta(hours=hours_ago),
        source="Source",
        category=category,
        body=body,
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
    html = build_email_html([], time_window_hours=12)

    assert "No articles found in the last 12 hours" in html


def test_ut_006_6_truncation_message_display():
    msg = "Showing 5 of 10 articles"
    html = build_email_html([_article("A")], truncation_message=msg)

    assert msg in html


def test_ut_006_7_render_inline_body():
    body_text = "This is a secret message.\nMultiple lines."
    html = build_email_html([_article("Body Test", body=body_text)])

    assert body_text in html
    assert "article-body" in html


def test_ut_006_8_render_without_link():
    html = build_email_html([_article("No Link Test", link="")])

    assert "No Link Test" in html
    assert 'href=""' not in html
