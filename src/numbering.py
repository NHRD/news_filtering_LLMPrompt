"""Assign sequential numbers to articles sorted by category then publication date."""

from typing import List, NamedTuple

try:
    from . import Article
except ImportError:  # pragma: no cover
    from __init__ import Article


class NumberedArticle(NamedTuple):
    no: int
    article: Article


def number_articles(articles):
    # type: (List[Article]) -> List[NumberedArticle]
    """Assign global sequential numbers to articles.

    Ordering:
    1. Categories sorted alphabetically.
    2. Within each category, articles sorted by ``published`` descending (newest first).
    3. Sequential integers starting at 1 across all categories.

    Returns a list of NumberedArticle in ascending ``no`` order.
    """
    # Collect unique categories in sorted order
    categories = sorted({a.category for a in articles})

    numbered = []
    counter = 1
    for category in categories:
        cat_articles = [a for a in articles if a.category == category]
        cat_articles.sort(key=lambda a: a.published, reverse=True)
        for article in cat_articles:
            numbered.append(NumberedArticle(no=counter, article=article))
            counter += 1

    return numbered
