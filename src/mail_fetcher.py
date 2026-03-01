"""Gmail IMAP mailing list fetcher.

Fetches emails from configured Gmail label folders and converts them to Article objects.
Uses only Python stdlib (imaplib, email) — no additional dependencies.

Each article's `body` contains the email's text/plain content embedded directly,
allowing recipients to read mailing list content inline in the digest HTML without
needing to follow any external links.

On any IMAP failure, logs a WARNING and returns an empty list so the pipeline
continues with RSS articles only (graceful degradation).
"""

import imaplib
import logging
import socket
from datetime import datetime, timezone
from email import message_from_bytes
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional

try:
    from . import Article
    from .config import MailFetchConfig, MailingListEntry
except ImportError:  # pragma: no cover
    from __init__ import Article
    from config import MailFetchConfig, MailingListEntry

logger = logging.getLogger(__name__)

# IMAP SEARCH SINCE expects "DD-Mon-YYYY" (e.g. "01-Mar-2026")
_IMAP_DATE_FORMAT = "%d-%b-%Y"


def _decode_subject(raw_subject):
    # type: (Optional[str]) -> str
    """Decode RFC 2047 encoded email subject to a plain string."""
    if not raw_subject:
        return "(no subject)"
    parts = decode_header(raw_subject)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            enc = charset or "utf-8"
            try:
                decoded.append(part.decode(enc, errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded.append(part.decode("utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_plain_text(msg):
    # type: (object) -> str
    """Extract text/plain body from an email message.

    Walks all parts (works for both multipart and non-multipart messages)
    and returns the content of the first text/plain part that is not an attachment.
    Returns empty string if no suitable text/plain part is found.
    """
    for part in msg.walk():
        if part.get_content_type() != "text/plain":
            continue
        if "attachment" in str(part.get("Content-Disposition", "")):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            return payload.decode("utf-8", errors="replace")
    return ""


def _parse_date(raw_date):
    # type: (Optional[str]) -> Optional[datetime]
    """Parse email Date header into an offset-aware UTC datetime."""
    if not raw_date:
        return None
    try:
        dt = parsedate_to_datetime(raw_date)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _fetch_single_list(imap_conn, entry, cutoff):
    # type: (imaplib.IMAP4_SSL, MailingListEntry, datetime) -> List[Article]
    """Fetch Article objects for one MailingListEntry.

    Selects the Gmail label folder, searches for messages since `cutoff`,
    and fetches full RFC822 messages to extract subject and body.
    Returns an empty list on any failure so the caller can continue with other lists.
    """
    articles = []  # type: List[Article]
    since_str = cutoff.strftime(_IMAP_DATE_FORMAT)

    try:
        folder = '"{}"'.format(entry.label) if " " in entry.label else entry.label
        status, _ = imap_conn.select(folder)
        if status != "OK":
            logger.warning("[Mail Fetcher] Failed to select label '%s'", entry.label)
            return []

        logger.info("[Mail Fetcher] Fetching list: %s (label:%s)", entry.name, entry.label)

        status, data = imap_conn.search(None, '(SINCE "{}")'.format(since_str))
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = data[0].split()
        for msg_id in message_ids:
            try:
                status, raw = imap_conn.fetch(msg_id, "(RFC822)")
                if status != "OK" or not raw or raw[0] is None:
                    continue
                raw_bytes = raw[0][1]
                if not isinstance(raw_bytes, bytes):
                    continue

                msg = message_from_bytes(raw_bytes)

                subject = _decode_subject(msg.get("Subject"))
                published = _parse_date(msg.get("Date"))
                if published is None:
                    logger.warning("[Mail Fetcher] Skipping message with no date: %s", subject)
                    continue

                body = _extract_plain_text(msg)

                articles.append(Article(
                    title=subject,
                    link="",  # No external link for mail articles
                    published=published,
                    source=entry.name,
                    category=entry.category,
                    body=body,
                ))
            except Exception as exc:
                logger.warning("[Mail Fetcher] Failed to parse message %s: %s", msg_id, exc)

    except Exception as exc:
        logger.warning("[Mail Fetcher] Failed to fetch list '%s': %s", entry.name, exc)

    return articles


def fetch_mail_articles(config, cutoff):
    # type: (MailFetchConfig, datetime) -> List[Article]
    """Fetch mailing list emails from Gmail IMAP and return as Article objects.

    - Returns empty list immediately if config.enabled is False.
    - On IMAP connection or auth failure, logs WARNING and returns empty list.
    - Per-list failures also log WARNING and are skipped; other lists continue.
    """
    if not config.enabled:
        return []
    if not config.lists:
        return []

    try:
        logger.info("[Mail Fetcher] Connecting to %s:%s", config.imap_server, config.imap_port)
        imap_conn = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
    except (OSError, socket.error, imaplib.IMAP4.error) as exc:
        logger.warning("[Mail Fetcher] Connection failed: %s. Skipping mail fetch.", exc)
        return []

    try:
        imap_conn.login(config.imap_user, config.imap_password)
    except imaplib.IMAP4.error as exc:
        logger.warning("[Mail Fetcher] Authentication failed: %s. Skipping mail fetch.", exc)
        try:
            imap_conn.logout()
        except Exception:
            pass
        return []

    all_articles = []  # type: List[Article]
    try:
        for entry in config.lists:
            articles = _fetch_single_list(imap_conn, entry, cutoff)
            logger.info(
                "[Mail Fetcher] Fetched %d articles from '%s'", len(articles), entry.name
            )
            all_articles.extend(articles)
    finally:
        try:
            imap_conn.logout()
        except Exception:
            pass

    return all_articles
