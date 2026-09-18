import asyncio
import threading

import pytest
from app.core.config import Settings
from app.integrations.registration_mail import SmtpRegistrationMailer
from pydantic import ValidationError


async def test_cancelled_requests_keep_real_smtp_work_bounded(monkeypatch) -> None:
    release = threading.Event()
    started = threading.Event()
    mailer = SmtpRegistrationMailer(
        Settings(
            smtp_enabled=True,
            smtp_host="smtp.example.com",
            smtp_from_email="sender@example.com",
            smtp_tls_mode="tls",
            smtp_username="",
            smtp_password="",
        )
    )

    def send(_email: str, _code: str) -> None:
        started.set()
        release.wait(timeout=5)

    monkeypatch.setattr(mailer, "_send", send)
    task = asyncio.create_task(mailer.send_code("synthetic@example.com", "123456"))
    try:
        assert await asyncio.to_thread(started.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # The HTTP request ended, but its actual worker still owns a slot.
        assert len(mailer._pending) == 1
        assert mailer._slots._value == 3
    finally:
        release.set()
        await asyncio.gather(*mailer._pending, return_exceptions=True)
    assert not mailer._pending
    assert mailer._slots._value == 4


@pytest.mark.parametrize(
    "options",
    [
        {"smtp_host": ""},
        {"smtp_from_email": None},
        {
            "smtp_tls_mode": "none",
            "smtp_username": "smtp-user",
            "smtp_password": "synthetic-password",
        },
        {"smtp_username": "smtp-user", "smtp_password": ""},
    ],
)
def test_enabled_smtp_configuration_fails_closed(options) -> None:
    values = dict(
        smtp_enabled=True,
        smtp_host="smtp.example.com",
        smtp_from_email="sender@example.com",
        smtp_tls_mode="tls",
        smtp_username="",
        smtp_password="",
    )
    with pytest.raises(ValidationError):
        Settings(**{**values, **options})
