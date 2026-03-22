"""Build HTML email content from articles."""

import itertools
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from . import Article
    from .numbering import NumberedArticle
except ImportError:  # pragma: no cover
    from __init__ import Article
    from numbering import NumberedArticle


def _group_articles(numbered_articles):
    # type: (List[NumberedArticle]) -> List[Dict[str, object]]
    """Group NumberedArticle list by category, preserving no-ascending order.

    Uses itertools.groupby which requires the input to already be sorted by
    category (Article Numbering guarantees categories are alphabetically
    ordered and no is monotonically increasing).
    """
    categories = []  # type: List[Dict[str, object]]
    for cat_name, group in itertools.groupby(numbered_articles, key=lambda na: na.article.category):
        cat_items = list(group)
        # Build a list of dicts for the template
        article_dicts = [
            {
                "no": na.no,
                "title_ja": na.article.title_ja if na.article.title_ja else na.article.title,
                "title": na.article.title,
                "link": na.article.link,
                "source": na.article.source,
                "published": na.article.published,
            }
            for na in cat_items
        ]
        categories.append({"name": cat_name, "articles": article_dicts})
    return categories


def _articles_to_numbered(articles):
    # type: (List[Article]) -> List[NumberedArticle]
    """Convert a plain Article list to NumberedArticle for backward compatibility.

    Groups by category (sorted alphabetically), sorts within category by
    published descending, then assigns sequential numbers starting at 1.
    """
    from collections import defaultdict

    grouped = defaultdict(list)  # type: Dict[str, List[Article]]
    for a in articles:
        grouped[a.category].append(a)

    numbered = []
    counter = 1
    for cat in sorted(grouped.keys()):
        for a in sorted(grouped[cat], key=lambda x: x.published, reverse=True):
            numbered.append(NumberedArticle(no=counter, article=a))
            counter += 1
    return numbered


def build_email_html(
    numbered_articles,
    template_path="templates/email.html",
    truncation_message="",
    time_window_hours=24,
):
    # type: (Union[List[NumberedArticle], List[Article]], str, str, int) -> str
    template_file = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_file.name)

    # Accept both List[NumberedArticle] (new path) and List[Article] (legacy/tests)
    if numbered_articles and isinstance(numbered_articles[0], Article):
        # Legacy: plain Article list – convert to NumberedArticle
        numbered = _articles_to_numbered(numbered_articles)  # type: ignore[arg-type]
        raw_articles = numbered_articles  # type: ignore[assignment]
    else:
        numbered = numbered_articles  # type: ignore[assignment]
        raw_articles = [na.article for na in numbered]  # type: ignore[union-attr]

    categories = _group_articles(numbered)

    if raw_articles:
        min_ts = min(a.published for a in raw_articles)
        max_ts = max(a.published for a in raw_articles)
    else:
        now = datetime.now(timezone.utc)
        min_ts = now
        max_ts = now

    source_count = len({a.source for a in raw_articles})
    return template.render(
        date_range=(
            f"{min_ts.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}"
            f" - {max_ts.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}"
        ),
        article_count=len(raw_articles),
        source_count=source_count,
        categories=categories,
        generation_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        truncation_message=truncation_message,
        time_window_hours=time_window_hours,
    )


def build_error_html(error_message, template_path="templates/error.html"):
    # type: (str, str) -> str
    template_file = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_file.name)
    return template.render(
        error_message=error_message,
        generation_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
