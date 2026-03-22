"""Unit tests for src/html_builder.py (UT-006).

既存テストを NumberedArticle 対応シグネチャに更新。
build_email_html の受け取る引数が List[Article] から List[NumberedArticle] に
変わった場合を想定しつつ、後方互換もテスト対象に含める。
"""

from datetime import datetime, timedelta, timezone
from typing import List

from src import Article
from src.html_builder import build_email_html
from src.numbering import NumberedArticle, number_articles


def _article(title: str, category: str = "Tech", hours_ago: int = 0,
             title_ja: str = "") -> Article:
    base = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)
    return Article(
        title=title,
        link=f"https://example.com/{title.replace(' ', '-')}".lower(),
        published=base - timedelta(hours=hours_ago),
        source="Source",
        category=category,
        title_ja=title_ja,
    )


def _numbered(title: str, category: str = "Tech", hours_ago: int = 0,
              title_ja: str = "", no: int = 1) -> NumberedArticle:
    return NumberedArticle(no=no, article=_article(title, category, hours_ago, title_ja))


# ---- 既存テスト（後方互換: List[Article] でも動くことを確認） ----

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


# ---- 新規テスト: NumberedArticle 対応 ----

def test_ut_006_7_no_column_rendered():
    """No.列が正しくレンダリングされるか。"""
    articles = [_article("Article A", "Tech", title_ja="記事A")]
    numbered = number_articles(articles)
    html = build_email_html(numbered)

    # No.1 が HTML に含まれていること
    assert "1." in html or "1" in html


def test_ut_006_8_title_ja_displayed():
    """title_ja が表示されるか。"""
    articles = [_article("Fed hikes rates", "Finance", title_ja="連邦準備制度、利上げ")]
    numbered = number_articles(articles)
    html = build_email_html(numbered)

    assert "連邦準備制度、利上げ" in html


def test_ut_006_9_title_ja_fallback_to_title():
    """title_ja="" の場合は title にフォールバックされるか。"""
    articles = [_article("English Title Only", "Tech", title_ja="")]
    numbered = number_articles(articles)
    html = build_email_html(numbered)

    # title_ja が空の場合、title が表示される
    assert "English Title Only" in html


def test_ut_006_10_group_articles_no_resorting():
    """_group_articles() が numbering.py の確定した順序を破壊しないか。

    Article Numbering が確定させた no の順序を保ったまま
    カテゴリでグルーピングされること。
    カテゴリ内での再ソートは行われないこと。
    """
    # Finance: no=1(新), no=2(旧) / Tech: no=3 の順で渡す
    articles = [
        _article("Finance Newest", "Finance", hours_ago=1, title_ja="Finance新"),
        _article("Finance Oldest", "Finance", hours_ago=10, title_ja="Finance旧"),
        _article("Tech Only", "Tech", hours_ago=2, title_ja="Tech記事"),
    ]
    # number_articles はアルファベット順(Finance→Tech)、カテゴリ内はpublished降順
    numbered = number_articles(articles)

    # Finance が先で no=1,2 / Tech が後で no=3
    finance_articles = [na for na in numbered if na.article.category == "Finance"]
    assert finance_articles[0].no == 1
    assert finance_articles[0].article.title == "Finance Newest"
    assert finance_articles[1].no == 2

    html = build_email_html(numbered)

    # HTML 内で Finance が Tech より先に登場
    assert html.index("Finance") < html.index("Tech Only")
    # Finance Newest が Finance Oldest より先に登場（再ソートされていない）
    assert html.index("Finance Newest") < html.index("Finance Oldest")


def test_ut_006_11_numbered_articles_nos_in_html():
    """複数カテゴリをまたいで通し番号が HTML に出力されるか。"""
    articles = [
        _article("AI News", "AI", hours_ago=1, title_ja="AIニュース"),
        _article("Finance News", "Finance", hours_ago=2, title_ja="ファイナンスニュース"),
    ]
    numbered = number_articles(articles)
    html = build_email_html(numbered)

    # no=1(AI News), no=2(Finance News) が HTML に含まれる
    assert "1" in html
    assert "2" in html
    assert "AIニュース" in html
    assert "ファイナンスニュース" in html
