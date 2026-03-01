from datetime import datetime, timedelta, timezone
from email.header import Header
from email.message import EmailMessage
from email.utils import format_datetime

from src.config import MailFetchConfig, MailingListEntry
from src.mail_fetcher import fetch_mail_articles


def _mail_config(entries, enabled=True):
    return MailFetchConfig(
        enabled=enabled,
        imap_server="imap.gmail.com",
        imap_port=993,
        imap_user="sender@example.com",
        imap_password="secret",
        timeout_seconds=30,
        lists=entries,
    )


def _entry(label="ml/security"):
    return MailingListEntry(name="Security ML", category="Security", label=label)


def _email_bytes(subject, date_dt, plain_body=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["Date"] = format_datetime(date_dt)
    msg["From"] = "list@example.com"
    msg["To"] = "sender@example.com"
    if plain_body is not None:
        msg.set_content(plain_body)
    else:
        msg.set_content("")
    return msg.as_bytes()


class FakeIMAP:
    def __init__(self, search_data=None, fetch_bytes=None):
        self.search_data = search_data if search_data is not None else b"1"
        self.fetch_bytes = fetch_bytes
        self.login_calls = []
        self.select_calls = []
        self.search_calls = []
        self.logout_called = False

    def login(self, user, password):
        self.login_calls.append((user, password))
        return "OK", [b"logged in"]

    def select(self, mailbox):
        self.select_calls.append(mailbox)
        return "OK", [b"1"]

    def search(self, charset, criteria):
        self.search_calls.append((charset, criteria))
        return "OK", [self.search_data]

    def fetch(self, msg_id, _query):
        return "OK", [(b"1", self.fetch_bytes)]

    def logout(self):
        self.logout_called = True
        return "BYE", [b"bye"]


def test_ut_009_1_imap_connect_and_login(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    msg_bytes = _email_bytes(
        subject="Hello",
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
        plain_body="Test body",
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    calls = {}

    def fake_imap_ctor(host, port):
        calls["host"] = host
        calls["port"] = port
        return fake

    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", fake_imap_ctor)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert calls == {"host": "imap.gmail.com", "port": 993}
    assert fake.login_calls == [("sender@example.com", "secret")]
    assert len(articles) == 1
    assert articles[0].body == "Test body\n"  # EmailMessage appends newline


def test_ut_009_3_search_by_label_uses_select_and_since(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    msg_bytes = _email_bytes(
        subject="Label query",
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry("ml/security")])

    fetch_mail_articles(cfg, cutoff=cutoff)

    assert fake.select_calls[0] == "ml/security"
    assert fake.search_calls[0][1] == '(SINCE "17-Feb-2026")'


def test_ut_009_4_decode_rfc2047_subject(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    encoded_subject = Header("日本語テスト", "utf-8").encode()
    msg_bytes = _email_bytes(
        subject=encoded_subject,
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles[0].title == "日本語テスト"


def test_ut_009_5_date_header_to_utc(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    jst = timezone(timedelta(hours=9))
    msg_bytes = _email_bytes(
        subject="Date TZ",
        date_dt=datetime(2026, 2, 17, 21, 0, tzinfo=jst),  # -> 12:00 UTC
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles[0].published.tzinfo == timezone.utc
    assert articles[0].published.hour == 12


def test_ut_009_14_extract_text_plain_body(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    msg_bytes = _email_bytes(
        subject="Plain Body",
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
        plain_body="Line 1\nLine 2",
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles[0].body == "Line 1\nLine 2\n"


def test_ut_009_15_link_is_always_empty_for_mail(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    msg_bytes = _email_bytes(
        subject="No Link",
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles[0].link == ""


def test_ut_009_9_connection_failure_returns_empty(monkeypatch, caplog):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "src.mail_fetcher.imaplib.IMAP4_SSL",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("network down")),
    )
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles == []
    assert "Connection failed" in caplog.text


def test_ut_009_10_disabled_returns_empty_without_imap(monkeypatch):
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    calls = {"count": 0}

    def fake_ctor(*a, **kw):
        calls["count"] += 1
        return FakeIMAP(fetch_bytes=b"")

    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", fake_ctor)
    cfg = _mail_config([_entry()], enabled=False)

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles == []
    assert calls["count"] == 0


def test_ut_009_12_label_with_spaces_is_quoted(monkeypatch):
    """Labels containing spaces should be quoted in the SELECT command."""
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    msg_bytes = _email_bytes(
        subject="Spaced Label",
        date_dt=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
    )
    fake = FakeIMAP(fetch_bytes=msg_bytes)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry("Tech news")])

    fetch_mail_articles(cfg, cutoff=cutoff)

    assert fake.select_calls[0] == '"Tech news"'


def test_ut_009_16_imap_zero_results_returns_empty(monkeypatch):
    """IMAP SEARCH returning 0 hits should result in an empty list, not an error."""
    cutoff = datetime(2026, 2, 17, 0, 0, tzinfo=timezone.utc)
    fake = FakeIMAP(search_data=b"", fetch_bytes=None)
    monkeypatch.setattr("src.mail_fetcher.imaplib.IMAP4_SSL", lambda *a, **kw: fake)
    cfg = _mail_config([_entry()])

    articles = fetch_mail_articles(cfg, cutoff=cutoff)

    assert articles == []
