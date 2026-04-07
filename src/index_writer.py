"""Write numbered articles to a JSON index file with FIFO rotation."""

import glob
import json
import logging
import os
from datetime import datetime, timezone
from typing import List

try:
    from .config import AppConfig
    from .numbering import NumberedArticle
except ImportError:  # pragma: no cover
    from config import AppConfig
    from numbering import NumberedArticle

logger = logging.getLogger(__name__)


def write_index(numbered, config):
    # type: (List[NumberedArticle], AppConfig) -> None
    """Write numbered articles to a JSON index file and apply FIFO rotation.

    Session is determined by current local hour: < 12 -> "AM", else -> "PM".
    I/O errors are logged at ERROR level and swallowed so the pipeline continues.
    """
    now = datetime.now()
    session = "AM" if now.hour < 12 else "PM"
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")
    filename = f"news_index_{date_str}_{time_str}.json"

    index_dir = config.index.index_dir
    try:
        os.makedirs(index_dir, exist_ok=True)
    except OSError as exc:
        logger.error("[IndexWriter] Failed to create index directory '%s': %s", index_dir, exc)
        return

    filepath = os.path.join(index_dir, filename)

    run_time = datetime.now(timezone.utc).isoformat()

    articles_data = []
    for na in numbered:
        a = na.article
        articles_data.append(
            {
                "no": na.no,
                "title_ja": a.title_ja,
                "title_en": a.title,
                "link": a.link,
                "source": a.source,
                "category": a.category,
                "published": a.published.isoformat(),
            }
        )

    index_data = {
        "session": session,
        "run_time": run_time,
        "article_count": len(numbered),
        "articles": articles_data,
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        logger.info("[IndexWriter] Saved index to %s (%d articles)", filepath, len(numbered))
    except OSError as exc:
        logger.error("[IndexWriter] Failed to write index file '%s': %s", filepath, exc)
        return

    # FIFO rotation
    try:
        pattern = os.path.join(index_dir, "news_index_*.json")
        existing = sorted(glob.glob(pattern))
        max_files = config.index.max_files
        while len(existing) > max_files:
            oldest = existing.pop(0)
            try:
                os.remove(oldest)
                logger.info("[IndexWriter] Removed old index file: %s", oldest)
            except OSError as exc:
                logger.error("[IndexWriter] Failed to remove old index file '%s': %s", oldest, exc)
    except OSError as exc:
        logger.error("[IndexWriter] FIFO rotation error: %s", exc)
