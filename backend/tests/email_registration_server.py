"""Local-only SMTP/API harness for Web and native registration acceptance.

Run: uv run python -m tests.email_registration_server
Uses one isolated schema in the existing PostgreSQL service and local SMTP capture.
Never mounted by the production application.
"""

import asyncio
import re
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

import uvicorn
from app.core.composition import build_api_runtime
from app.core.config import RateLimitPolicy, Settings
from app.core.db import Base, create_session_factory
from app.main import create_app
from app.models.auth import UserRow
from app.models.provider_catalog import ProviderCatalogEntryRow
from fastapi import FastAPI
from sqlalchemy import select
from tests.postgres import isolated_postgres_engine

codes = {}
inbox = FastAPI()


@inbox.get("/code")
async def code(email: str):
    return {"code": codes.get(email)}


async def smtp(reader, writer):
    writer.write(b"220 local capture SMTP\r\n")
    await writer.drain()
    try:
        while line := await reader.readline():
            if line.upper().startswith(b"DATA"):
                writer.write(b"354 send\r\n")
                await writer.drain()
                body = b""
                while (part := await reader.readline()) not in (b".\r\n", b""):
                    body += part
                message = BytesParser(policy=policy.default).parsebytes(body)
                codes[str(message["To"])] = re.search(
                    r"\b[0-9]{6}\b", message.get_content()
                ).group()
                writer.write(b"250 accepted\r\n")
            elif line.upper().startswith(b"EHLO"):
                writer.write(b"250-localhost\r\n250 SIZE 10240\r\n")
            else:
                writer.write(b"250 OK\r\n")
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    async with isolated_postgres_engine() as engine:
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        async with create_session_factory(engine).begin() as session:
            session.add(
                ProviderCatalogEntryRow(
                    key="youtube",
                    display_name="YouTube",
                    sort_order=1,
                    is_visible=True,
                    is_deleted=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        smtp_server = await asyncio.start_server(smtp, "127.0.0.1", 18125)
        settings = Settings(
            app_env="test",
            smtp_enabled=True,
            smtp_host="127.0.0.1",
            smtp_port=18125,
            smtp_tls_mode="none",
            smtp_username="",
            smtp_password="",
            smtp_from_email="qa@example.com",
            request_fingerprint_secret="email-qa-isolated-admission-key-20260908-v2",
            rate_limit_policies={
                "registration_code": RateLimitPolicy(limit=100, window_seconds=3600),
                "register": RateLimitPolicy(limit=100, window_seconds=3600),
            },
        )
        with patch("app.core.composition.create_engine", return_value=engine):
            runtime = build_api_runtime(settings)
        app = create_app(settings, runtime=runtime)
        api_server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=18112, log_level="warning")
        )
        inbox_server = uvicorn.Server(
            uvicorn.Config(inbox, host="127.0.0.1", port=18113, log_level="warning")
        )
        try:
            print(
                "QA API 18112; local SMTP capture 18125; "
                "test-only inbox 18113; isolated database schema",
                flush=True,
            )
            await asyncio.gather(api_server.serve(), inbox_server.serve())
        finally:
            async with engine.connect() as c:
                ids = (await c.execute(select(UserRow.id))).scalars().all()
            for uid in ids:
                await runtime.auth_session_store.delete_user_sessions(uid)
            await runtime.close()
            smtp_server.close()
            await smtp_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
