"""Create the first administrator from the deployment host, without email transport."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.db import create_engine, create_session_factory
from app.integrations.passwords import Argon2PasswordHasher
from app.models.auth import UserRow
from app.services.auth.service import _validate_password
from app.services.auth.usernames import normalize_username
from dotenv import dotenv_values
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def create_first_admin(
    sessions: async_sessionmaker[AsyncSession],
    *,
    username: str,
    email: str,
    password: str,
) -> bool:
    """Return False when any account exists; lock the table before checking."""
    display, normalized_username = normalize_username(username)
    normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).casefold()
    _validate_password(password)
    password_hash = await Argon2PasswordHasher().hash(password)
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        # The DB operator already has write access; this lock also serializes
        # concurrent first-install invocations and ordinary registrations.
        await session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
        if await session.scalar(select(UserRow.id).limit(1)) is not None:
            return False
        session.add(
            UserRow(
                id=uuid4(),
                username=display,
                normalized_username=normalized_username,
                email=normalized_email,
                password_hash=password_hash,
                role="admin",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="初始化空库中的首位管理员")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        parser.error("password input requires a local interactive terminal")
    password = getpass.getpass("管理员密码：")
    confirmation = getpass.getpass("再次输入管理员密码：")
    if password != confirmation:
        parser.error("passwords do not match")
    try:
        database_url = load_database_url(args.env_file)
    except ValueError as exc:
        parser.error(str(exc))

    async def run() -> bool:
        engine = create_engine(database_url)
        try:
            return await create_first_admin(
                create_session_factory(engine),
                username=args.username,
                email=args.email,
                password=password,
            )
        finally:
            await engine.dispose()

    try:
        created = asyncio.run(run())
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if not created:
        print("用户表非空；首管理员初始化未执行")
        return 2
    print("首管理员已创建；现在可通过 Web 登录")
    return 0


def load_database_url(env_file: Path) -> str:
    """Use the explicitly selected deployment file, never a shell override."""
    if not env_file.is_file():
        raise ValueError("environment file does not exist")
    database_url = dotenv_values(env_file).get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    return database_url


if __name__ == "__main__":
    raise SystemExit(main())
