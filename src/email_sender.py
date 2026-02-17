"""Gmail SMTP sender with retry."""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from .config import EmailConfig
except ImportError:  # pragma: no cover
    from config import EmailConfig


def send_email(config, subject, html_body):
    # type: (EmailConfig, str, str) -> bool
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = ", ".join(config.recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with smtplib.SMTP(config.smtp_server, config.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(config.sender_email, config.sender_password)
                server.sendmail(config.sender_email, config.recipients, msg.as_string())
            logging.info("[Email Sender] Sent to %s recipients", len(config.recipients))
            return True
        except smtplib.SMTPAuthenticationError:
            logging.error("[Email Sender] Authentication failed")
            raise
        except Exception as exc:
            if attempt >= max_retries:
                logging.error("[Email Sender] Failed after %s attempts: %s", max_retries, exc)
                raise
            wait_seconds = 2 ** (attempt - 1)
            logging.warning(
                "[Email Sender] Attempt %s/%s failed: %s. Retrying in %ss",
                attempt,
                max_retries,
                exc,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    return False
