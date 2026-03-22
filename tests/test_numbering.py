"""Unit tests for src/numbering.py (UT-010)."""

from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from src import Article
from src.numbering import NumberedArticle, number_articles


def _make_article(title: str, category: str = "Tech", hours_ago: int = 0) -> Article:
    base = datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc)
    return Article(
        title=title,
        link=f"https://example.com/{title.replace(' ', '-').lower()}",
        published=base - timedelta(hours=hours_ago),
        source="Source",
        category=category,
    )


# UT-010-1: 単一カテゴリ: 1から連番
def test_ut_010_1_single_category_sequential_from_1():
    articles = [
        _make_article("Article A", "Tech", hours_ago=2),
        _make_article("Article B", "Tech", hours_ago=5),
        _make_article("Article C", "Tech", hours_ago=1),
    ]

    result = number_articles(articles)

    assert len(result) == 3
    nos = [na.no for na in result]
    assert nos == [1, 2, 3]
    # no=1 が最新（hours_ago=1）
    assert result[0].no == 1
    assert result[0].article.title == "Article C"


# UT-010-2: 複数カテゴリ: アルファベット順に並び通し番号
def test_ut_010_2_multiple_categories_alphabetical_order():
    articles = [
        _make_article("Tech1", "Tech", hours_ago=1),
        _make_article("Finance1", "Finance", hours_ago=2),
        _make_article("Tech2", "Tech", hours_ago=3),
        _make_article("AI1", "AI", hours_ago=4),
    ]

    result = number_articles(articles)

    assert len(result) == 4
    # カテゴリはアルファベット順: AI, Finance, Tech
    # AI(1件) → Finance(1件) → Tech(2件) の順に番号が付く
    category_order = [na.article.category for na in result]
    assert category_order[0] == "AI"
    assert category_order[1] == "Finance"
    assert category_order[2] == "Tech"
    assert category_order[3] == "Tech"

    nos = [na.no for na in result]
    assert nos == [1, 2, 3, 4]


# UT-010-3: カテゴリ内: published降順ソート（newest first）
def test_ut_010_3_within_category_published_desc():
    articles = [
        _make_article("Old", "Tech", hours_ago=10),
        _make_article("Newest", "Tech", hours_ago=1),
        _make_article("Middle", "Tech", hours_ago=5),
    ]

    result = number_articles(articles)

    assert result[0].article.title == "Newest"
    assert result[1].article.title == "Middle"
    assert result[2].article.title == "Old"


# UT-010-4: 空リスト → 空リストを返す
def test_ut_010_4_empty_list():
    result = number_articles([])

    assert result == []


# UT-010-5: NumberedArticle の no が連続している（途切れなし）
def test_ut_010_5_sequential_numbers_no_gap():
    articles = [_make_article(f"Article {i}", "Tech", hours_ago=i) for i in range(10)]

    result = number_articles(articles)

    nos = [na.no for na in result]
    assert nos == list(range(1, 11))


# UT-010-6: 複数カテゴリの通し番号がカテゴリをまたいで連続する
def test_ut_010_6_cross_category_sequential():
    articles = [
        _make_article("A1", "Alpha", hours_ago=1),
        _make_article("A2", "Alpha", hours_ago=2),
        _make_article("B1", "Beta", hours_ago=1),
    ]

    result = number_articles(articles)

    # Alpha: no=1,2 → Beta: no=3
    alpha_articles = [na for na in result if na.article.category == "Alpha"]
    beta_articles = [na for na in result if na.article.category == "Beta"]

    assert alpha_articles[0].no == 1
    assert alpha_articles[1].no == 2
    assert beta_articles[0].no == 3
