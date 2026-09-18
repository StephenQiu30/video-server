"""Bounded SMTP transport; never logs recipients, codes or SMTP responses."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import Settings
from app.services.auth.errors import AuthError, AuthErrorCode


class SmtpRegistrationMailer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._slots = asyncio.Semaphore(4)
        self._pending: set[asyncio.Task[None]] = set()

    async def send_code(self, email: str, code: str) -> None:
        if not self._settings.smtp_enabled:
            raise AuthError(AuthErrorCode.EMAIL_UNAVAILABLE)
        try:
            async with asyncio.timeout(20):
                await self._slots.acquire()
                operation = asyncio.create_task(
                    asyncio.to_thread(self._send, email, code)
                )
                self._pending.add(operation)
                operation.add_done_callback(self._completed)
                await asyncio.shield(operation)
        except (OSError, TimeoutError, ValueError):
            raise AuthError(AuthErrorCode.EMAIL_SEND_FAILED) from None

    def _completed(self, operation: asyncio.Task[None]) -> None:
        self._pending.discard(operation)
        self._slots.release()
        if not operation.cancelled():
            operation.exception()

    def _send(self, email: str, code: str) -> None:
        settings = self._settings
        message = EmailMessage()
        message["Subject"] = "帧取注册验证码"
        message["From"] = formataddr(
            (settings.smtp_from_name, str(settings.smtp_from_email))
        )
        message["To"] = email
        message["Message-ID"] = make_msgid()
        message.set_content(
            f"你的帧取注册验证码是：{code}\n\n"
            "10 分钟内有效，请勿向他人透露。\n如非本人操作，请忽略此邮件。"
        )
        context = ssl.create_default_context()
        smtp = (
            smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=3, context=context
            )
            if settings.smtp_tls_mode == "tls"
            else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=3)
        )
        try:
            if settings.smtp_tls_mode == "starttls":
                smtp.starttls(context=context)
            if settings.smtp_username:
                smtp.login(
                    settings.smtp_username, settings.smtp_password.get_secret_value()
                )
            refused = smtp.send_message(message)
            if refused:
                raise OSError("recipient refused")
        finally:
            # DATA acceptance is the boundary; QUIT failures must not undo success.
            smtp.close()
