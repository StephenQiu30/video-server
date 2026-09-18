"""Atomic resend and one-time verification shared by Web and App."""

import hmac
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.email_verification import EmailVerificationRow


class SqlAlchemyVerificationStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def reserve(
        self,
        email: str,
        generation: UUID,
        digest: str,
        now: datetime,
        expires_at: datetime,
    ) -> bool:
        values = dict(
            email=email,
            generation=generation,
            code_digest=digest,
            requested_at=now,
            expires_at=expires_at,
            attempts=0,
            sent=False,
            consumed=False,
        )
        statement = insert(EmailVerificationRow).values(**values)
        upsert = statement.on_conflict_do_update(
            index_elements=[EmailVerificationRow.email],
            set_=values,
            where=EmailVerificationRow.requested_at <= now - timedelta(seconds=60),
        ).returning(EmailVerificationRow.email)
        async with self._sessions.begin() as session:
            await session.execute(
                delete(EmailVerificationRow).where(
                    EmailVerificationRow.expires_at < now - timedelta(days=1)
                )
            )
            return await session.scalar(upsert) is not None

    async def mark_sent(self, email: str, generation: UUID) -> bool:
        async with self._sessions.begin() as session:
            value = await session.scalar(
                update(EmailVerificationRow)
                .where(
                    EmailVerificationRow.email == email,
                    EmailVerificationRow.generation == generation,
                    EmailVerificationRow.consumed.is_(False),
                )
                .values(sent=True)
                .returning(EmailVerificationRow.email)
            )
            return value is not None

    async def invalidate(self, email: str, generation: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(EmailVerificationRow)
                .where(
                    EmailVerificationRow.email == email,
                    EmailVerificationRow.generation == generation,
                )
                .values(consumed=True, sent=False)
            )

    async def consume(self, email: str, digest: str, now: datetime) -> bool:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                select(EmailVerificationRow)
                .where(EmailVerificationRow.email == email)
                .with_for_update()
            )
            if row is None or not row.sent or row.consumed or row.expires_at <= now:
                return False
            if row.attempts >= 5:
                return False
            row.attempts += 1
            if not hmac.compare_digest(row.code_digest, digest):
                return False
            row.consumed = True
            return True
