"""Translate article titles from English to Japanese using Gemini CLI."""

import logging
import re
import os
import subprocess
import time
from typing import List

try:
    from . import Article
    from .config import AppConfig
except ImportError:  # pragma: no cover
    from __init__ import Article
    from config import AppConfig

logger = logging.getLogger(__name__)

_LINE_RE = re.compile(r"^(\d+)\.\s+(.+)$")


class TranslationError(Exception):
    """Raised when translation fails and on_translate_failure == 'fail'."""


def _build_prompt(lines):
    # type: (List[str]) -> str
    lines_text = "\n".join(lines)
    return (
        "ソフトウェア開発のドキュメント作業として、以下の英語ニュースタイトルを日本語に翻訳してください。\n"
        "出力は「番号. 翻訳テキスト」の形式で1行ずつ返してください。説明文は不要です。\n"
        "例:\n"
        "1. 連邦準備制度、政策金利を0.25%引き上げ\n"
        "2. Appleが次世代チップを発表\n\n"
        f"{lines_text}"
    )


def _translate_batch(articles, on_translate_failure, model="gemini-2.5-flash-lite"):
    # type: (List[Article], str, str) -> List[Article]
    """Translate a single batch of articles (batch-local 1-based numbering)."""
    lines = [f"{i + 1}. {a.title}" for i, a in enumerate(articles)]
    prompt = _build_prompt(lines)

    try:
        result = subprocess.run(
            ["/home/naohisa-harada/.nvm/versions/node/v22.22.1/bin/gemini", "-m", model, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy(),
        )
        result.check_returncode()
        output = result.stdout.strip()
    except Exception as exc:
        stderr = getattr(exc, "stderr", None)
        logger.warning("[Translator] Gemini CLI error: %s | stderr: %s", exc, stderr)
        if on_translate_failure == "fail":
            raise TranslationError(f"Translation failed: {exc}") from exc
        return [a._replace(title_ja=a.title) for a in articles]

    parsed = {}  # type: dict
    for line in output.splitlines():
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        n = int(m.group(1))
        if n < 1 or n > len(articles):
            logger.warning(
                "[Translator] Out-of-range number %d in translation output (batch size %d)",
                n,
                len(articles),
            )
            continue
        if n in parsed:
            logger.warning("[Translator] Duplicate number %d in translation output; using last occurrence", n)
        parsed[n] = m.group(2).strip()

    if not parsed:
        logger.warning("[Translator] All lines failed to parse or empty output")
        if on_translate_failure == "fail":
            raise TranslationError("Translation output could not be parsed")
        return [a._replace(title_ja=a.title) for a in articles]

    result_articles = []
    for i, article in enumerate(articles):
        title_ja = parsed.get(i + 1, article.title)
        if (i + 1) not in parsed:
            logger.warning(
                "[Translator] No translation for article %d ('%s'); using original title",
                i + 1,
                article.title,
            )
        result_articles.append(article._replace(title_ja=title_ja))
    return result_articles


def translate_articles(articles, config):
    # type: (List[Article], AppConfig) -> List[Article]
    """Translate article titles to Japanese using Gemini CLI.

    Processes articles in batches of translation.batch_size with 1-based local
    numbering per batch.  Returns a new list with title_ja filled in.
    """
    if not articles:
        return articles

    batch_size = config.translation.batch_size
    on_failure = config.translation.on_translate_failure

    if len(articles) <= batch_size:
        return _translate_batch(articles, on_failure, model=config.gemini.model)

    interval = config.translation.batch_interval_seconds
    translated = []
    for start in range(0, len(articles), batch_size):
        batch = articles[start : start + batch_size]
        translated.extend(_translate_batch(batch, on_failure, model=config.gemini.model))
        if start + batch_size < len(articles):
            time.sleep(interval)

    return translated
