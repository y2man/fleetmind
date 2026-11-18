import logging
import smtplib
import ssl
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger("fleetmind.email")
RESEND_EMAILS_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, body: str) -> bool:
    """Send through Resend, then SMTP, or log in development when no provider is configured.

    Never raises: a mail outage must not turn a sign-up or an invitation into a server error after the
    database change was already saved. Returns True if the message was handed to the mail server.
    The body (which holds one-time links) is only logged in console mode, never when SMTP is configured.
    """
    s = get_settings()
    if s.resend_api_key:
        try:
            response = httpx.post(
                RESEND_EMAILS_URL,
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                json={"from": s.email_from or s.smtp_from, "to": [to], "subject": subject, "text": body},
                timeout=15.0,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("EMAIL Resend send failed to=%s subject=%s error_type=%s", to, subject, type(exc).__name__)
            return False
    if not s.smtp_host:
        logger.warning("EMAIL (console backend, set SMTP_HOST to send) to=%s subject=%s\n%s", to, subject, body)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
    msg.set_content(body)
    try:
        if s.smtp_port == 465:
            server = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15)
        with server:
            if s.smtp_port != 465:
                server.starttls(context=ssl.create_default_context())
            if s.smtp_user:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("EMAIL send failed to=%s subject=%s", to, subject)
        return False
