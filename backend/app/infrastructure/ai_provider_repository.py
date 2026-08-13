"""SQLAlchemy persistence for AI analysis Provider profiles."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ai_providers import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderProfile,
    DuplicateAiProviderKeyError,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import AiProviderProfileRow


class SqlAlchemyAiProviderRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_profiles(self) -> tuple[AiProviderProfile, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(AiProviderProfileRow).order_by(
                        AiProviderProfileRow.is_active.desc(),
                        AiProviderProfileRow.created_at,
                        AiProviderProfileRow.key,
                    )
                )
            ).all()
        return tuple(_to_domain(row) for row in rows)

    async def get_profile(self, key: str) -> AiProviderProfile | None:
        async with self._sessions() as session:
            row = await session.get(AiProviderProfileRow, key)
        return _to_domain(row) if row is not None else None

    async def get_active_profile(self) -> AiProviderProfile | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AiProviderProfileRow).where(
                    AiProviderProfileRow.is_active.is_(True)
                )
            )
        return _to_domain(row) if row is not None else None

    async def create_profile(
        self,
        *,
        key: str,
        display_name: str,
        engine: AiProviderEngine,
        auth_mode: AiProviderAuthMode,
        base_url: str | None,
        model: str,
        credential_ciphertext: bytes | None,
        credential_key_id: str | None,
        now: datetime,
    ) -> AiProviderProfile:
        row = AiProviderProfileRow(
            key=key,
            display_name=display_name,
            engine=engine.value,
            auth_mode=auth_mode.value,
            base_url=base_url,
            model=model,
            credential_ciphertext=credential_ciphertext,
            credential_key_id=credential_key_id,
            is_active=False,
            created_at=now,
            updated_at=now,
        )
        try:
            async with self._sessions.begin() as session:
                session.add(row)
                await session.flush()
        except IntegrityError as exc:
            raise DuplicateAiProviderKeyError from exc
        return _to_domain(row)

    async def update_profile(
        self,
        key: str,
        *,
        display_name: str | None,
        engine: AiProviderEngine | None,
        auth_mode: AiProviderAuthMode | None,
        base_url: str | None,
        base_url_changed: bool,
        model: str | None,
        credential_ciphertext: bytes | None,
        credential_key_id: str | None,
        credential_changed: bool,
        now: datetime,
    ) -> AiProviderProfile | None:
        values: dict[str, object] = {"updated_at": now}
        if display_name is not None:
            values["display_name"] = display_name
        if engine is not None:
            values["engine"] = engine.value
        if auth_mode is not None:
            values["auth_mode"] = auth_mode.value
        if base_url_changed:
            values["base_url"] = base_url
        if model is not None:
            values["model"] = model
        if credential_changed:
            values["credential_ciphertext"] = credential_ciphertext
            values["credential_key_id"] = credential_key_id
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(AiProviderProfileRow)
                .where(AiProviderProfileRow.key == key)
                .values(**values)
                .returning(AiProviderProfileRow)
            )
        return _to_domain(row) if row is not None else None

    async def activate_profile(
        self, key: str, *, now: datetime
    ) -> AiProviderProfile | None:
        async with self._sessions.begin() as session:
            exists = await session.scalar(
                select(AiProviderProfileRow.key).where(AiProviderProfileRow.key == key)
            )
            if exists is None:
                return None
            await session.execute(
                update(AiProviderProfileRow)
                .where(AiProviderProfileRow.is_active.is_(True))
                .values(is_active=False, updated_at=now)
            )
            row = await session.scalar(
                update(AiProviderProfileRow)
                .where(AiProviderProfileRow.key == key)
                .values(is_active=True, updated_at=now)
                .returning(AiProviderProfileRow)
            )
        return _to_domain(row) if row is not None else None

    async def delete_profile(self, key: str) -> bool:
        async with self._sessions.begin() as session:
            row = await session.get(AiProviderProfileRow, key)
            if row is None:
                return False
            await session.delete(row)
        return True


def _to_domain(row: AiProviderProfileRow) -> AiProviderProfile:
    return AiProviderProfile(
        key=row.key,
        display_name=row.display_name,
        engine=AiProviderEngine(row.engine),
        auth_mode=AiProviderAuthMode(row.auth_mode),
        base_url=row.base_url,
        model=row.model,
        credential_ciphertext=row.credential_ciphertext,
        credential_key_id=row.credential_key_id,
        is_active=row.is_active,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )
