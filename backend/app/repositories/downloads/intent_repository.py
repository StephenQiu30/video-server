"""Short PostgreSQL transactions own intent acceptance, execution and recovery.

Network work happens after claim and before completion, never under a row lock.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.download import DownloadJobRow
from app.models.download_intent import DownloadIntentRow
from app.models.media import MediaInspectionRow
from app.models.outbox import OutboxEventRow
from app.repositories.downloads.access_repository import cancel_job_row
from app.repositories.downloads.media_repository import insert_inspection
from app.repositories.errors import (
    IdempotencyConflict,
    LeaseConflict,
    RepositoryConflict,
    RepositoryNotFound,
)
from app.repositories.quota_admission import (
    ensure_active_capacity,
    lock_admission,
    reserve,
)
from app.services.downloads.inspection_models import EncryptedUrl, InspectionCreate
from app.services.downloads.intent_models import (
    IntentCreate,
    IntentHistoryEntry,
    IntentHistoryPage,
    IntentLease,
    IntentSnapshot,
    IntentStatus,
)
from app.services.downloads.validation import (
    media_kind_from_metadata,
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.services.provider_access import ProviderAccessPolicy
from app.services.quotas import DEFAULT_USER_QUOTA, QuotaPolicy, UserQuota

_RUNNING = ("preparing", "resolving")
_TERMINAL = ("cancelled", "expired", "failed", "handed_off")
_BUDGET = timedelta(seconds=180)


class IntentRepository:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        quota_policy: QuotaPolicy | None = None,
    ) -> None:
        self._sessions = sessions
        self._quota_policy = quota_policy or QuotaPolicy()

    async def accept(
        self,
        command: IntentCreate,
        *,
        now: datetime,
        quota: UserQuota = DEFAULT_USER_QUOTA,
    ) -> IntentSnapshot:
        validate_now(now)
        validate_owner_hash(command.owner_hash)
        validate_idempotency_key(command.idempotency_key)
        if len(command.request_fingerprint) != 64:
            raise ValueError("invalid intent fingerprint")
        async with self._sessions() as session, session.begin():
            await lock_admission(session, command.owner_hash)
            existing = await session.scalar(
                select(DownloadIntentRow).where(
                    DownloadIntentRow.owner_hash == command.owner_hash,
                    DownloadIntentRow.idempotency_key == command.idempotency_key,
                )
            )
            if existing is not None:
                if (
                    existing.request_fingerprint != command.request_fingerprint
                    or not _same_public_scope(
                        existing.access_policy, command.access_policy
                    )
                ):
                    raise IdempotencyConflict("intent idempotency key already used")
                return _snapshot(existing)
            await reserve(
                session,
                self._quota_policy,
                owner_hash=command.owner_hash,
                resource_id=command.id,
                kind="inspection",
                now=now,
                quota=quota,
            )
            row = await session.scalar(
                insert(DownloadIntentRow)
                .values(
                    id=command.id,
                    owner_hash=command.owner_hash,
                    idempotency_key=command.idempotency_key,
                    request_fingerprint=command.request_fingerprint,
                    url_ciphertext=command.url.ciphertext,
                    url_nonce=command.url.nonce,
                    url_key_id=command.url.key_id,
                    access_policy=command.access_policy.value,
                    deadline=now + _BUDGET,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_download_intents_owner_key")
                .returning(DownloadIntentRow)
            )
            if row is None:
                row = await session.scalar(
                    select(DownloadIntentRow).where(
                        DownloadIntentRow.owner_hash == command.owner_hash,
                        DownloadIntentRow.idempotency_key == command.idempotency_key,
                    )
                )
                if row is None:
                    raise RepositoryConflict("intent disappeared during acceptance")
                if (
                    row.request_fingerprint != command.request_fingerprint
                    or not _same_public_scope(row.access_policy, command.access_policy)
                ):
                    raise IdempotencyConflict("intent idempotency key already used")
            else:
                session.add(_requested(row, now))
            # Context manager commits both records before returning to the caller.
            return _snapshot(row)

    async def get(self, intent_id: UUID, owner_hash: str) -> IntentSnapshot:
        async with self._sessions() as session:
            row = await self._owned(session, intent_id, owner_hash)
            return _snapshot(row)

    async def get_by_key(self, idempotency_key: str, owner_hash: str) -> IntentSnapshot:
        async with self._sessions() as session:
            row = await session.scalar(
                select(DownloadIntentRow).where(
                    DownloadIntentRow.owner_hash == owner_hash,
                    DownloadIntentRow.idempotency_key == idempotency_key,
                )
            )
            if row is None:
                raise RepositoryNotFound("intent not found")
            return _snapshot(row)

    async def cancel(
        self, intent_id: UUID, owner_hash: str, *, now: datetime
    ) -> IntentSnapshot:
        validate_now(now)
        async with self._sessions() as session, session.begin():
            row = await self._owned(session, intent_id, owner_hash, lock=True)
            if row.status == "handed_off":
                job = await session.scalar(
                    select(DownloadJobRow)
                    .where(
                        DownloadJobRow.id == row.job_id,
                        DownloadJobRow.owner_hash == owner_hash,
                    )
                    .with_for_update()
                )
                if job is None:
                    raise RepositoryConflict("intent download is unavailable")
                cancel_job_row(job, now)
                _transition(row, "cancelled", now, "cancelled")
            if row.status not in _TERMINAL:
                _transition(row, "cancelled", now, "cancelled")
            return _snapshot(row)

    async def history(
        self, owner_hash: str, *, before: UUID | None = None, limit: int = 20
    ) -> IntentHistoryPage:
        validate_owner_hash(owner_hash)
        if not 1 <= limit <= 50:
            raise ValueError("invalid history page size")
        async with self._sessions() as session:
            query = (
                select(DownloadIntentRow, MediaInspectionRow.title)
                .outerjoin(
                    MediaInspectionRow,
                    and_(
                        MediaInspectionRow.id == DownloadIntentRow.inspection_id,
                        MediaInspectionRow.owner_hash == owner_hash,
                    ),
                )
                .where(DownloadIntentRow.owner_hash == owner_hash)
            )
            if before is not None:
                cursor = await self._owned(session, before, owner_hash)
                query = query.where(
                    or_(
                        DownloadIntentRow.created_at < cursor.created_at,
                        and_(
                            DownloadIntentRow.created_at == cursor.created_at,
                            DownloadIntentRow.id < cursor.id,
                        ),
                    )
                )
            rows = (
                await session.execute(
                    query.order_by(
                        DownloadIntentRow.created_at.desc(), DownloadIntentRow.id.desc()
                    ).limit(limit + 1)
                )
            ).all()
            items = tuple(
                IntentHistoryEntry(_snapshot(row), title) for row, title in rows[:limit]
            )
            return IntentHistoryPage(
                items, items[-1].intent.id if len(rows) > limit else None
            )

    async def claim(
        self, intent_id: UUID, worker_id: str, *, now: datetime, lease_for: timedelta
    ) -> IntentLease | None:
        validate_now(now)
        if not worker_id.strip() or len(worker_id) > 128 or lease_for <= timedelta(0):
            raise ValueError("invalid intent lease")
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(DownloadIntentRow)
                .where(
                    DownloadIntentRow.id == intent_id,
                    DownloadIntentRow.status == "queued",
                )
                .with_for_update()
            )
            if row is None:
                return None
            if _exhausted(row, now):
                _expire(row, now)
                return None
            _transition(row, "resolving", now)
            row.attempt += 1
            row.fence += 1
            row.lease_owner = worker_id
            row.lease_expires_at = min(row.deadline, now + lease_for)
            return IntentLease(
                _snapshot(row),
                EncryptedUrl(row.url_ciphertext, row.url_nonce, row.url_key_id),
            )

    async def refresh(
        self,
        intent_id: UUID,
        owner_hash: str,
        *,
        now: datetime,
        quota: UserQuota = DEFAULT_USER_QUOTA,
    ) -> IntentSnapshot:
        validate_now(now)
        validate_owner_hash(owner_hash)
        async with self._sessions() as session, session.begin():
            await lock_admission(session, owner_hash)
            row = await self._owned(session, intent_id, owner_hash, lock=True)
            if row.status in (*_RUNNING, "queued", "retry_wait", "handed_off"):
                return _snapshot(row)
            if row.status != "ready" or row.inspection_id is None:
                raise RepositoryConflict("intent cannot refresh in this state")
            previous = await session.get(MediaInspectionRow, row.inspection_id)
            if previous is None or previous.owner_hash != owner_hash:
                raise RepositoryConflict("intent result is unavailable")
            if previous.expires_at > now:
                return _snapshot(row)
            # Waiting for a format choice was not active work. Only the saved
            # remainder is available; neither attempt nor budget is reset.
            if row.remaining_budget_ms <= 0 or row.attempt >= row.max_attempts:
                _transition(row, "expired", now, "resource_expired")
                return _snapshot(row)
            if not quota.exempt:
                await ensure_active_capacity(
                    session, quota.apply(self._quota_policy), owner_hash
                )
            row.deadline = now + timedelta(milliseconds=row.remaining_budget_ms)
            _transition(row, "queued", now)
            session.add(_requested(row, now))
            return _snapshot(row)

    async def heartbeat(
        self, lease: IntentSnapshot, *, now: datetime, lease_for: timedelta
    ) -> bool:
        validate_now(now)
        if lease_for <= timedelta(0):
            raise ValueError("invalid intent lease")
        async with self._sessions() as session, session.begin():
            row = await self._leased(session, lease, now)
            if row is None:
                return False
            # Heartbeats do not change the execution version or fencing token.
            row.lease_expires_at = min(row.deadline, now + lease_for)
            row.updated_at = now
            row.remaining_budget_ms = _remaining(row, now)
            return True

    async def complete(
        self, lease: IntentSnapshot, result: InspectionCreate, *, now: datetime
    ) -> IntentSnapshot:
        """Inspection, formats and ready status commit atomically behind fencing."""
        validate_now(now)
        async with self._sessions() as session, session.begin():
            row = await self._leased(session, lease, now)
            if row is None:
                raise LeaseConflict("intent execution ownership lost")
            if (
                result.owner_hash != row.owner_hash
                or result.metadata.get("access_policy_id") != row.access_policy
                or result.expires_at <= now
            ):
                raise RepositoryConflict("inspection does not match intent scope")
            # This namespace is reserved for durable intent results; clients never
            # select its inspection key or reuse another intent's result.
            if result.idempotency_key != f"intent:{row.id}:{row.fence}":
                raise RepositoryConflict("inspection does not match intent identity")
            if row.inspection_id is not None:
                previous = await session.get(MediaInspectionRow, row.inspection_id)
                if previous is None or (
                    previous.owner_hash != row.owner_hash
                    or previous.extractor_key != result.extractor_key
                    or previous.provider_media_id != result.provider_media_id
                    or media_kind_from_metadata(previous.metadata_json)
                    != media_kind_from_metadata(result.metadata)
                ):
                    _transition(row, "failed", now, "unsupported_source")
                    return _snapshot(row)
            await insert_inspection(session, result)
            row.inspection_id = result.id
            _transition(row, "ready", now)
            return _snapshot(row)

    async def fail(
        self,
        lease: IntentSnapshot,
        *,
        now: datetime,
        reason_code: str,
        retry_at: datetime | None = None,
        preparation_wait: bool = False,
    ) -> IntentSnapshot:
        validate_now(now)
        if not reason_code or len(reason_code) > 64:
            raise ValueError("invalid intent reason")
        if retry_at is not None:
            validate_now(retry_at)
            if retry_at <= now:
                raise ValueError("retry must be scheduled in the future")
        async with self._sessions() as session, session.begin():
            row = await self._leased(session, lease, now)
            if row is None:
                raise LeaseConflict("intent execution ownership lost")
            if preparation_wait:
                if (
                    row.access_policy != ProviderAccessPolicy.PUBLIC_SESSION.value
                    or reason_code != "provider_guest_context_required"
                    or row.attempt < 1
                ):
                    raise ValueError("invalid guest preparation wait")
                row.attempt -= 1
            if (
                retry_at is not None
                and row.attempt < row.max_attempts
                and retry_at < row.deadline
            ):
                _transition(row, "retry_wait", now, reason_code)
                row.retry_at = retry_at
            else:
                _transition(row, "failed", now, reason_code)
            return _snapshot(row)

    async def recover(
        self,
        *,
        now: datetime,
        limit: int = 100,
        queued_stale_for: timedelta = timedelta(seconds=30),
    ) -> int:
        """Recover lost deliveries/leases and due retries with bounded locked scans."""
        validate_now(now)
        if not 1 <= limit <= 200 or queued_stale_for <= timedelta(0):
            raise ValueError("invalid intent recovery bounds")
        async with self._sessions() as session, session.begin():
            rows = (
                await session.scalars(
                    select(DownloadIntentRow)
                    .where(
                        DownloadIntentRow.status.in_(
                            ("queued", "retry_wait", *_RUNNING)
                        ),
                        or_(
                            DownloadIntentRow.deadline <= now,
                            and_(
                                DownloadIntentRow.status == "queued",
                                DownloadIntentRow.updated_at <= now - queued_stale_for,
                            ),
                            and_(
                                DownloadIntentRow.status == "retry_wait",
                                DownloadIntentRow.retry_at <= now,
                            ),
                            and_(
                                DownloadIntentRow.status.in_(_RUNNING),
                                DownloadIntentRow.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .order_by(DownloadIntentRow.updated_at, DownloadIntentRow.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                if _exhausted(row, now):
                    _expire(row, now)
                else:
                    _transition(row, "queued", now, row.reason_code)
                    session.add(_requested(row, now))
            return len(rows)

    @staticmethod
    async def _owned(
        session: AsyncSession, intent_id: UUID, owner_hash: str, *, lock: bool = False
    ) -> DownloadIntentRow:
        statement = select(DownloadIntentRow).where(
            DownloadIntentRow.id == intent_id,
            DownloadIntentRow.owner_hash == owner_hash,
        )
        row = await session.scalar(statement.with_for_update() if lock else statement)
        if row is None:
            raise RepositoryNotFound("intent does not exist")
        return row

    @staticmethod
    async def _leased(
        session: AsyncSession, lease: IntentSnapshot, now: datetime
    ) -> DownloadIntentRow | None:
        row: DownloadIntentRow | None = await session.scalar(
            select(DownloadIntentRow)
            .where(
                DownloadIntentRow.id == lease.id,
                DownloadIntentRow.status.in_(_RUNNING),
                DownloadIntentRow.lease_owner == lease.lease_owner,
                DownloadIntentRow.fence == lease.fence,
                DownloadIntentRow.version == lease.version,
                DownloadIntentRow.lease_expires_at > now,
                DownloadIntentRow.deadline > now,
            )
            .with_for_update()
        )
        return row


def _same_public_scope(stored: str, requested: ProviderAccessPolicy) -> bool:
    # Routing availability can change after restart; the original intent keeps
    # its frozen route. Public guest state grants no additional account rights.
    public = {ProviderAccessPolicy.PUBLIC, ProviderAccessPolicy.PUBLIC_SESSION}
    return stored == requested or (stored in public and requested in public)


def _remaining(row: DownloadIntentRow, now: datetime) -> int:
    return max(
        0,
        min(row.remaining_budget_ms, int((row.deadline - now).total_seconds() * 1000)),
    )


def _exhausted(row: DownloadIntentRow, now: datetime) -> bool:
    return _remaining(row, now) == 0 or row.attempt >= row.max_attempts


def _expire(row: DownloadIntentRow, now: datetime) -> None:
    _transition(
        row,
        "expired" if _remaining(row, now) == 0 else "failed",
        now,
        "inspection_timeout" if _remaining(row, now) == 0 else "inspection_failed",
    )


def _transition(
    row: DownloadIntentRow, status: str, now: datetime, reason: str | None = None
) -> None:
    row.status = status
    row.version += 1
    row.lease_owner = None
    row.lease_expires_at = None
    row.retry_at = None
    row.reason_code = reason
    row.remaining_budget_ms = _remaining(row, now)
    row.updated_at = now


def _requested(row: DownloadIntentRow, now: datetime) -> OutboxEventRow:
    return OutboxEventRow(
        id=uuid4(),
        aggregate_type="download_intent",
        aggregate_id=row.id,
        aggregate_version=row.version,
        event_type="download.intent.requested",
        payload={"intent_id": str(row.id), "version": row.version},
        available_at=now,
        created_at=now,
    )


def _snapshot(row: DownloadIntentRow) -> IntentSnapshot:
    return IntentSnapshot(
        id=row.id,
        owner_hash=row.owner_hash,
        status=IntentStatus(row.status),
        access_policy=ProviderAccessPolicy(row.access_policy),
        version=row.version,
        fence=row.fence,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        remaining_budget_ms=row.remaining_budget_ms,
        deadline=row.deadline,
        lease_owner=row.lease_owner,
        lease_expires_at=row.lease_expires_at,
        retry_at=row.retry_at,
        inspection_id=row.inspection_id,
        job_id=row.job_id,
        reason_code=row.reason_code,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
