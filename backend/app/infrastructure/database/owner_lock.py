"""Serialize owner-wide admission across resource types and API processes."""

import hashlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_owner(session: AsyncSession, owner_hash: str) -> None:
    digest = hashlib.sha256(f"video:owner-admission:{owner_hash}".encode()).digest()
    key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
