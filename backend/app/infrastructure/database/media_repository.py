"""Atomic inspection and format persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .contracts import InspectionCreate, InspectionCreateResult, InspectionSnapshot
from .errors import IdempotencyConflict, RepositoryNotFound
from .mapping import inspection_snapshot
from .models import MediaFormatRow, MediaInspectionRow
from .repository_base import RepositoryBase


class MediaRepository(RepositoryBase):
    async def save_inspection(
        self, command: InspectionCreate
    ) -> InspectionCreateResult:
        """Persist encrypted URL metadata and all semantic formats together."""
        async with self._sessions() as session:
            try:
                async with session.begin():
                    existing = await session.scalar(
                        select(MediaInspectionRow).where(
                            MediaInspectionRow.owner_hash == command.owner_hash,
                            MediaInspectionRow.idempotency_key
                            == command.idempotency_key,
                        )
                    )
                    if existing is not None:
                        if existing.request_fingerprint != command.request_fingerprint:
                            raise IdempotencyConflict(
                                "inspection idempotency key already used"
                            )
                        return InspectionCreateResult(
                            await self._snapshot(session, existing), created=False
                        )
                    row = MediaInspectionRow(
                        id=command.id,
                        owner_hash=command.owner_hash,
                        idempotency_key=command.idempotency_key,
                        request_fingerprint=command.request_fingerprint,
                        url_ciphertext=command.url_ciphertext,
                        url_nonce=command.url_nonce,
                        url_key_id=command.url_key_id,
                        extractor_key=command.extractor_key,
                        provider_media_id=command.provider_media_id,
                        title=command.title,
                        duration_seconds=command.duration_seconds,
                        metadata_json=command.metadata,
                        expires_at=command.expires_at,
                    )
                    session.add(row)
                    await session.flush()
                    format_rows = tuple(
                        MediaFormatRow(
                            id=item.id,
                            inspection_id=command.id,
                            display_name=item.display_name,
                            plan_fingerprint=item.plan_fingerprint,
                            semantic_plan=item.semantic_plan,
                            provider_hints=item.provider_hints,
                            expires_at=item.expires_at,
                        )
                        for item in command.formats
                    )
                    session.add_all(format_rows)
                    await session.flush()
                    result = InspectionCreateResult(
                        inspection_snapshot(row, format_rows), created=True
                    )
                return result
            except IntegrityError as exc:
                await session.rollback()
                existing = await session.scalar(
                    select(MediaInspectionRow).where(
                        MediaInspectionRow.owner_hash == command.owner_hash,
                        MediaInspectionRow.idempotency_key == command.idempotency_key,
                    )
                )
                if existing is None:
                    raise
                if existing.request_fingerprint != command.request_fingerprint:
                    raise IdempotencyConflict(
                        "inspection idempotency key already used"
                    ) from exc
                return InspectionCreateResult(
                    await self._snapshot(session, existing), created=False
                )

    async def get_inspection(
        self, inspection_id: UUID, owner_hash: str, now: datetime
    ) -> InspectionSnapshot:
        del now
        async with self._sessions() as session:
            row = await session.scalar(
                select(MediaInspectionRow).where(
                    MediaInspectionRow.id == inspection_id,
                    MediaInspectionRow.owner_hash == owner_hash,
                )
            )
            if row is None:
                raise RepositoryNotFound("media inspection does not exist")
            return await self._snapshot(session, row)

    @staticmethod
    async def _snapshot(
        session: AsyncSession,
        row: MediaInspectionRow,
        *,
        now: datetime | None = None,
    ) -> InspectionSnapshot:
        statement = select(MediaFormatRow).where(MediaFormatRow.inspection_id == row.id)
        if now is not None:
            statement = statement.where(MediaFormatRow.expires_at > now)
        formats = tuple(
            (await session.scalars(statement.order_by(MediaFormatRow.id))).all()
        )
        return inspection_snapshot(row, formats)
