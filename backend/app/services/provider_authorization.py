"""Durable administrator source maintenance; a readable source is not a grant."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.services.provider_types import ProviderAuthorizationSource, ProviderKey

_MAX_REQUEST_BYTES = 256
_DEFAULT_RESULT_RETENTION = timedelta(hours=24)
_logger = logging.getLogger(__name__)


class ProviderAuthorizationStatus:
    PENDING = "pending"
    SOURCE_AVAILABLE = "source_available"
    AUTHORIZATION_REQUIRED = "authorization_required"
    PERMISSION_REQUIRED = "permission_required"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProviderAuthorizationTransaction:
    transaction_id: str
    provider_key: str
    status: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthorizationRecord:
    id: UUID
    user_id: UUID
    provider_key: str
    source: ProviderAuthorizationSource
    status: str
    expires_at: datetime

    def view(self) -> ProviderAuthorizationTransaction:
        return ProviderAuthorizationTransaction(
            self.id.hex, self.provider_key, self.status, self.expires_at
        )


class ProviderAuthorizationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


class AuthorizationPersistence(Protocol):
    async def accept(
        self,
        user_id: UUID,
        provider_key: str,
        source: ProviderAuthorizationSource,
        *,
        now: datetime,
        ttl: timedelta,
        retention: timedelta,
    ) -> tuple[AuthorizationRecord, bool]: ...
    async def get(
        self, transaction_id: UUID, user_id: UUID, *, now: datetime
    ) -> AuthorizationRecord: ...
    async def transition(
        self, record: AuthorizationRecord, target: str, *, now: datetime
    ) -> AuthorizationRecord: ...
    async def pending(self, *, limit: int = 100) -> tuple[AuthorizationRecord, ...]: ...
    async def expired_results(
        self, *, now: datetime, limit: int = 100
    ) -> tuple[AuthorizationRecord, ...]: ...
    async def forget(self, record: AuthorizationRecord, *, now: datetime) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderAuthorizationRequest:
    """Non-secret authorization intent handed to the local queue adapter."""

    provider: ProviderKey
    expires_at: datetime
    source: ProviderAuthorizationSource = ProviderAuthorizationSource.DEDICATED_CHROME
    probe: bool = False

    def serialize(self) -> bytes:
        return json.dumps(
            {
                "provider": self.provider.value,
                "expires_at": self.expires_at.astimezone(UTC).isoformat(),
                "source": self.source.value,
                "probe": self.probe,
            },
            separators=(",", ":"),
        ).encode("ascii")

    @classmethod
    def parse(cls, payload: bytes) -> ProviderAuthorizationRequest:
        if not 0 < len(payload) <= _MAX_REQUEST_BYTES:
            raise ValueError("authorization request is outside the size limit")
        try:
            value = json.loads(payload.decode("ascii"))
            provider = ProviderKey(value["provider"])
            expires_at = datetime.fromisoformat(value["expires_at"])
            source = ProviderAuthorizationSource(
                value.get("source", ProviderAuthorizationSource.DEDICATED_CHROME.value)
            )
            probe = value.get("probe", False)
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid authorization request") from exc
        if expires_at.tzinfo is None or not isinstance(probe, bool):
            raise ValueError("authorization expiry must include a timezone")
        return cls(provider, expires_at.astimezone(UTC), source, probe)


class ProviderAuthorizationQueue(Protocol):
    """Filesystem or test adapter used by the authorization service."""

    def agent_ready(self, provider: ProviderKey) -> bool: ...

    def write_request(
        self, token: str, request: ProviderAuthorizationRequest
    ) -> None: ...

    def read_response(self, token: str) -> str | None: ...

    def remove_response(self, token: str) -> None: ...

    def cancel(self, token: str) -> None: ...

    def cleanup(self, token: str) -> None: ...


class ProviderAuthorizationService:
    """PostgreSQL owns transactions; bounded reconciliation is page-independent."""

    def __init__(
        self,
        authorization_queue: ProviderAuthorizationQueue,
        repository: AuthorizationPersistence,
        *,
        now: Callable[[], datetime],
        can_authorize_provider: Callable[[str], bool],
        transaction_ttl: timedelta = timedelta(minutes=10),
        result_retention: timedelta = _DEFAULT_RESULT_RETENTION,
    ) -> None:
        if transaction_ttl.total_seconds() <= 0:
            raise ValueError("provider authorization transaction TTL must be positive")
        if result_retention.total_seconds() <= 0:
            raise ValueError("provider authorization result retention must be positive")
        self._authorization_queue = authorization_queue
        self._repository = repository
        self._now = now
        self._can_authorize_provider = can_authorize_provider
        self._ttl = transaction_ttl
        self._result_retention = result_retention
        self._task: asyncio.Task[None] | None = None

    async def begin(
        self,
        user_id: UUID,
        provider_key: str,
        source: ProviderAuthorizationSource = (
            ProviderAuthorizationSource.CURRENT_CHROME
        ),
    ) -> ProviderAuthorizationTransaction:
        try:
            provider = ProviderKey(provider_key)
            source = ProviderAuthorizationSource(source)
        except ValueError as exc:
            raise ProviderAuthorizationError(
                "provider_unsupported", "该平台没有可用的本机授权流程。"
            ) from exc
        if not self._can_authorize_provider(provider_key):
            raise ProviderAuthorizationError(
                "provider_unsupported", "该平台没有可用的本机授权流程。"
            )
        if not await asyncio.to_thread(self._authorization_queue.agent_ready, provider):
            raise ProviderAuthorizationError(
                "provider_configuration_missing",
                "本机授权 Agent 尚未安装，请先完成一次本机初始化。",
            )
        record, created = await self._repository.accept(
            user_id,
            provider_key,
            source,
            now=self._now(),
            ttl=self._ttl,
            retention=self._result_retention,
        )
        if created:
            try:
                self._authorization_queue.write_request(
                    record.id.hex,
                    ProviderAuthorizationRequest(provider, record.expires_at, source),
                )
            except Exception:
                # Preserve the failed operation for diagnosis; never acknowledge
                # a source whose control request was not durably published.
                await self._repository.transition(
                    record, ProviderAuthorizationStatus.FAILED, now=self._now()
                )
                raise ProviderAuthorizationError(
                    "provider_authorization_unavailable",
                    "本机授权队列暂时不可用，请检查本机 Agent 状态。",
                ) from None
        return record.view()

    async def get(
        self, user_id: UUID, transaction_id: str
    ) -> ProviderAuthorizationTransaction:
        record = await self._owned(user_id, transaction_id)
        return (await self._reconcile(record)).view()

    async def cancel(self, user_id: UUID, transaction_id: str) -> None:
        record = await self._owned(user_id, transaction_id)
        result = await self._repository.transition(
            record, ProviderAuthorizationStatus.CANCELLED, now=self._now()
        )
        if result.status in {
            ProviderAuthorizationStatus.CANCELLED,
            ProviderAuthorizationStatus.EXPIRED,
        }:
            self._authorization_queue.cancel(transaction_id)
            _remove_response_quietly(self._authorization_queue, transaction_id)

    async def _owned(self, user_id: UUID, transaction_id: str) -> AuthorizationRecord:
        if len(transaction_id) != 32 or any(
            c not in "0123456789abcdef" for c in transaction_id
        ):
            raise ProviderAuthorizationError("not_found", "授权事务不存在或已经过期。")
        return await self._repository.get(
            UUID(hex=transaction_id), user_id, now=self._now()
        )

    async def _reconcile(self, record: AuthorizationRecord) -> AuthorizationRecord:
        token = record.id.hex
        if record.status == ProviderAuthorizationStatus.PENDING:
            response = None
            if self._now() >= record.expires_at:
                target = ProviderAuthorizationStatus.EXPIRED
            else:
                response = self._authorization_queue.read_response(token)
                if response is None:
                    # The persisted pending operation is also its delivery intent.
                    # Re-publish idempotently after a crash between DB and queue.
                    self._authorization_queue.write_request(
                        token,
                        ProviderAuthorizationRequest(
                            ProviderKey(record.provider_key),
                            record.expires_at,
                            record.source,
                        ),
                    )
                    return record
                target = _response_status(response)
            # Commit before ACK/removing the response. Replays observe the same
            # terminal state; a concurrent cancellation cannot be overwritten.
            record = await self._repository.transition(record, target, now=self._now())
        # Retain a terminal queue marker until result retention ends. A delayed
        # publisher cannot reopen an already completed/cancelled host operation.
        self._authorization_queue.cancel(token)
        _remove_response_quietly(self._authorization_queue, token)
        return record

    async def reconcile(self) -> int:
        records = await self._repository.pending()
        completed = 0
        for record in records:
            try:
                async with asyncio.timeout(5):
                    result = await self._reconcile(record)
                completed += result.status != ProviderAuthorizationStatus.PENDING
            except Exception:
                # One bad queue entry must not stop other providers. Do not log
                # exception bodies: filesystem errors can disclose local paths.
                _logger.warning("provider authorization reconciliation failed")
        for record in await self._repository.expired_results(now=self._now()):
            self._authorization_queue.cleanup(record.id.hex)
            await self._repository.forget(record, now=self._now())
        return completed

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            try:
                async with asyncio.timeout(15):
                    await self.reconcile()
            except Exception:
                _logger.warning("provider authorization maintenance unavailable")
            await asyncio.sleep(2)

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None


def _response_status(value: str) -> str:
    if value == "source_available":
        return ProviderAuthorizationStatus.SOURCE_AVAILABLE
    if value == "cancelled":
        return ProviderAuthorizationStatus.CANCELLED
    if value == "expired":
        return ProviderAuthorizationStatus.EXPIRED
    if value == "credential_required":
        return ProviderAuthorizationStatus.AUTHORIZATION_REQUIRED
    if value == "provider_session_permission_denied":
        return ProviderAuthorizationStatus.PERMISSION_REQUIRED
    return ProviderAuthorizationStatus.FAILED


def _remove_response_quietly(
    authorization_queue: ProviderAuthorizationQueue, transaction_id: str
) -> None:
    try:
        authorization_queue.remove_response(transaction_id)
    except OSError:
        pass
