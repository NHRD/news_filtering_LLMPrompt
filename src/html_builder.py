"""Build HTML email content from articles."""

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from . import Article
except ImportError:  # pragma: no cover
    from __init__ import Article


def _group_articles(articles):
    # type: (List[Article]) -> List[Dict[str, object]]
    grouped = defaultdict(list)  # type: Dict[str, List[Article]]
    for article in articles:
        grouped[article.category].append(article)

    categories = []  # type: List[Dict[str, object]]
    for name in sorted(grouped.keys()):
        sorted_articles = sorted(grouped[name], key=lambda a: a.published, reverse=True)
        categories.append({"name": name, "articles": sorted_articles})
    return categories


def build_email_html(
    articles,
    template_path="templates/email.html",
):
    # type: (List[Article], str) -> str
    template_file = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_file.name)

    categories = _group_articles(articles)
    if articles:
        min_ts = min(a.published for a in articles)
        max_ts = max(a.published for a in articles)
    else:
        now = datetime.now(timezone.utc)
        min_ts = now
        max_ts = now

    source_count = len({a.source for a in articles})
    return template.render(
        date_range=(
            f"{min_ts.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}"
            f" - {max_ts.astimezone(timezone.utc):%Y-%m-%d %H:%M UTC}"
        ),
        article_count=len(articles),
        source_count=source_count,
        categories=categories,
        generation_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
