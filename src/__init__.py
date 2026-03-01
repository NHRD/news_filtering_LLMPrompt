"""Core data structures for RSS news filtering."""

from datetime import datetime
from typing import NamedTuple


class Article(NamedTuple):
    """Normalized article object used across the pipeline."""

    title: str
    link: str
    published: datetime
    source: str
    category: str
    body: str = ""
