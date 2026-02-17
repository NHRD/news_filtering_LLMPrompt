import smtplib
from unittest.mock import MagicMock

import pytest

from src.config import EmailConfig
from src.email_sender import send_email


def _email_config():
    return EmailConfig(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email="sender@example.com",
        sender_password="secret",
        recipients=["a@example.com", "b@example.com"],
        max_articles_per_email=200,
    )


def test_ut_007_1_send_email_mocked(monkeypatch):
    smtp = MagicMock()

    class SMTPContext:
        def __enter__(self):
            return smtp

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.email_sender.smtplib.SMTP", lambda *args, **kwargs: SMTPContext())

    ok = send_email(_email_config(), "Subject", "<h1>hello</h1>")

    assert ok is True
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("sender@example.com", "secret")
    smtp.sendmail.assert_called_once()


def test_ut_007_2_handle_auth_failure(monkeypatch):
    smtp = MagicMock()
    smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

    class SMTPContext:
        def __enter__(self):
            return smtp

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.email_sender.smtplib.SMTP", lambda *args, **kwargs: SMTPContext())

    with pytest.raises(smtplib.SMTPAuthenticationError):
        send_email(_email_config(), "Subject", "<h1>hello</h1>")


def test_ut_007_3_handle_network_error_with_retries(monkeypatch):
    calls = {"count": 0}

    class SMTPContext:
        def __enter__(self):
            calls["count"] += 1
            raise TimeoutError("network down")

        def __exit__(self, exc_type, exc, tb):
            return False

    sleep_mock = MagicMock()
    monkeypatch.setattr("src.email_sender.time.sleep", sleep_mock)
    monkeypatch.setattr("src.email_sender.smtplib.SMTP", lambda *args, **kwargs: SMTPContext())

    with pytest.raises(TimeoutError):
        send_email(_email_config(), "Subject", "<h1>hello</h1>")

    assert calls["count"] == 3
    assert sleep_mock.call_count == 2


def test_ut_007_4_multiple_recipients(monkeypatch):
    smtp = MagicMock()

    class SMTPContext:
        def __enter__(self):
            return smtp

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.email_sender.smtplib.SMTP", lambda *args, **kwargs: SMTPContext())

    cfg = _email_config()
    send_email(cfg, "Subject", "<h1>hello</h1>")

    args = smtp.sendmail.call_args[0]
    assert args[1] == ["a@example.com", "b@example.com"]
    assert "a@example.com, b@example.com" in args[2]
