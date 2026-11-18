"""Phase 9: SMTP sending (the mail server is replaced by a fake)."""
import smtplib

import pytest

from app.core.config import get_settings
from app.services import email as email_service


class FakeSMTP:
    instances: list = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.sent, self.started, self.login_args = host, port, [], False, None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        self.started = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    s = get_settings()
    for k, v in dict(
        smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
        smtp_from="FleetMind <no-reply@fleet.test>", resend_api_key="", email_from="",
    ).items():
        monkeypatch.setattr(s, k, v)
    return s


def test_console_mode_sends_nothing(caplog):
    assert email_service.send_email("a@b.com", "Hi", "link") is False
    assert FakeSMTP.instances == [] and "console backend" in caplog.text


def test_smtp_mode_uses_starttls_and_login(fake_smtp, monkeypatch):
    monkeypatch.setattr(fake_smtp, "smtp_host", "mail.test")
    monkeypatch.setattr(fake_smtp, "smtp_user", "u")
    monkeypatch.setattr(fake_smtp, "smtp_password", "p")
    assert email_service.send_email("a@b.com", "Reset", "the link") is True
    (srv,) = FakeSMTP.instances
    assert srv.host == "mail.test" and srv.started and srv.login_args == ("u", "p")
    msg = srv.sent[0]
    assert msg["To"] == "a@b.com" and msg["Subject"] == "Reset" and msg["From"].endswith("<no-reply@fleet.test>")


def test_port_465_uses_implicit_tls(fake_smtp, monkeypatch):
    monkeypatch.setattr(fake_smtp, "smtp_host", "mail.test")
    monkeypatch.setattr(fake_smtp, "smtp_port", 465)
    assert email_service.send_email("a@b.com", "x", "y") is True
    assert FakeSMTP.instances[0].started is False


def test_failure_is_logged_not_raised_and_body_not_leaked(fake_smtp, monkeypatch, caplog):
    monkeypatch.setattr(fake_smtp, "smtp_host", "mail.test")
    monkeypatch.setattr(FakeSMTP, "send_message", lambda self, m: (_ for _ in ()).throw(smtplib.SMTPException("down")))
    assert email_service.send_email("a@b.com", "Reset", "https://secret-link") is False
    assert "send failed" in caplog.text and "secret-link" not in caplog.text


def test_resend_is_used_when_configured(fake_smtp, monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(fake_smtp, "resend_api_key", "test-key")
    monkeypatch.setattr(fake_smtp, "email_from", "FleetMind <no-reply@fleet.test>")
    monkeypatch.setattr(email_service.httpx, "post", fake_post)

    assert email_service.send_email("a@b.com", "Reset", "one-time link") is True
    assert FakeSMTP.instances == []
    assert calls == [(
        email_service.RESEND_EMAILS_URL,
        {
            "headers": {"Authorization": "Bearer test-key"},
            "json": {"from": "FleetMind <no-reply@fleet.test>", "to": ["a@b.com"], "subject": "Reset", "text": "one-time link"},
            "timeout": 15.0,
        },
    )]


def test_resend_failure_is_not_retried_through_smtp(fake_smtp, monkeypatch, caplog):
    def fail_post(*args, **kwargs):
        raise email_service.httpx.TimeoutException("provider timeout")

    monkeypatch.setattr(fake_smtp, "resend_api_key", "test-key")
    monkeypatch.setattr(email_service.httpx, "post", fail_post)

    assert email_service.send_email("a@b.com", "Reset", "secret-link") is False
    assert FakeSMTP.instances == []
    assert "secret-link" not in caplog.text and "TimeoutException" in caplog.text
