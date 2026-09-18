import asyncio
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser

import pytest
from app.core.config import Settings
from app.core.db import create_session_factory
from app.crud.email_verification_repository import SqlAlchemyVerificationStore
from app.integrations.registration_mail import SmtpRegistrationMailer
from app.models.email_verification import EmailVerificationRow
from app.services.auth.email_verification import EmailVerification
from app.services.auth.errors import AuthError, AuthErrorCode
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.parametrize("reject", [False, True])
async def test_real_smtp_acceptance_and_rejection(
    postgres_engine: AsyncEngine, reject: bool
) -> None:
    messages: list[bytes] = []

    async def smtp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(b"220 localhost SMTP\r\n")
        await writer.drain()
        try:
            while line := await reader.readline():
                command = line.upper()
                if command.startswith(b"DATA"):
                    writer.write(b"354 send data\r\n")
                    await writer.drain()
                    body = b""
                    while (part := await reader.readline()) not in (b".\r\n", b""):
                        body += part
                    messages.append(body)
                    writer.write(b"550 rejected\r\n" if reject else b"250 accepted\r\n")
                elif command.startswith(b"EHLO"):
                    writer.write(b"250-localhost\r\n250 SIZE 10240\r\n")
                else:
                    writer.write(b"250 OK\r\n")
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(smtp, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    settings = Settings(
        app_env="test",
        smtp_enabled=True,
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_tls_mode="none",
        smtp_username="",
        smtp_password="",
        smtp_from_email="sender@example.com",
        smtp_from_name="帧取",
    )
    sessions = create_session_factory(postgres_engine)
    service = EmailVerification(
        SqlAlchemyVerificationStore(sessions),
        SmtpRegistrationMailer(settings),
        b"smtp-test-secret",
        lambda: datetime.now(UTC),
    )
    try:
        if reject:
            with pytest.raises(AuthError) as failure:
                await service.send("recipient@example.com")
            assert failure.value.code == AuthErrorCode.EMAIL_SEND_FAILED
        else:
            await service.send("recipient@example.com")
        assert len(messages) == 1
        message = BytesParser(policy=policy.default).parsebytes(messages[0])
        assert message["Subject"] == "帧取注册验证码"
        assert message["To"] == "recipient@example.com"
        assert "10 分钟" in str(message.get_content())
        async with sessions() as session:
            row = await session.get(EmailVerificationRow, "recipient@example.com")
            assert row is not None
            assert row.sent is not reject
            assert row.consumed is reject
    finally:
        server.close()
        await server.wait_closed()


async def test_unconfigured_email_fails_closed(postgres_engine: AsyncEngine) -> None:
    sessions = create_session_factory(postgres_engine)
    service = EmailVerification(
        SqlAlchemyVerificationStore(sessions),
        SmtpRegistrationMailer(Settings(smtp_enabled=False)),
        b"secret",
        lambda: datetime.now(UTC),
    )
    with pytest.raises(AuthError) as failure:
        await service.send("closed@example.com")
    assert failure.value.code == AuthErrorCode.EMAIL_UNAVAILABLE
    async with sessions() as session:
        row = await session.get(EmailVerificationRow, "closed@example.com")
        assert row is not None and row.consumed and not row.sent
