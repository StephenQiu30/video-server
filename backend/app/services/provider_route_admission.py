"""Persistent route admission shared by API, download worker and canary clients."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from app.services.provider_access import ProviderAccessPolicy, provider_access_policies
from app.services.provider_types import ProviderAccessContextRef

PROBE_LEASE = timedelta(seconds=60)
PROBE_TIMEOUT_SECONDS = 30
PROBE_LEASE_MARGIN = timedelta(seconds=5)
DEFAULT_COOLDOWN = timedelta(minutes=5)
MAX_COOLDOWN = timedelta(hours=1)
COOLDOWN_JITTER_RATIO = 0.2
SUCCESS_HYSTERESIS = 2


@dataclass(frozen=True, slots=True)
class ProviderRouteKey:
    provider_key: str
    access_policy_id: ProviderAccessPolicy
    egress_binding_id: str

    @classmethod
    def from_context(cls, context: ProviderAccessContextRef) -> ProviderRouteKey:
        # One controlled policy per provider is admitted. Cookie/engine revisions
        # deliberately do not participate: rotating them cannot reset a limit.
        policy = provider_access_policies(context.provider_key, (context.access_mode,))[
            0
        ]
        return cls(context.provider_key, policy, context.egress_affinity_id)


@dataclass(frozen=True, slots=True)
class ProviderRouteLease:
    key: ProviderRouteKey
    owner: str
    version: int | None
    expires_at: datetime | None = None


class RouteCoolingDown(RuntimeError):
    code = "provider_rate_limited"

    def __init__(self, retry_at: datetime):
        self.retry_at = retry_at
        super().__init__(self.code)


class RouteProbeTimeout(TimeoutError):
    code = "inspection_timeout"


class RouteAdmissionUnavailable(RuntimeError):
    code = "runner_dependency_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ProviderRouteCooldowns(Protocol):
    async def acquire(
        self, key: ProviderRouteKey, owner: str
    ) -> ProviderRouteLease: ...
    async def block(
        self,
        key: ProviderRouteKey,
        *,
        until: datetime,
        reason_code: str = "provider_rate_limited",
        stable_error_code: str | None = "provider_rate_limited",
    ) -> datetime: ...

    async def finish(
        self,
        lease: ProviderRouteLease,
        *,
        success: bool,
        reason_code: str = "probe_succeeded",
        stable_error_code: str | None = None,
    ) -> None: ...


class ProviderRouteCooldownReader(Protocol):
    async def retry_times(
        self, keys: tuple[ProviderRouteKey, ...]
    ) -> Mapping[ProviderRouteKey, datetime]: ...


class ProviderRouteAdmission:
    def __init__(self, repository: ProviderRouteCooldowns):
        self._repository = repository

    async def run[T](
        self,
        context: ProviderAccessContextRef,
        operation: Callable[[datetime | None], Awaitable[T]],
        *,
        owner: str | None = None,
        probe: Callable[[datetime | None], Awaitable[object]] | None = None,
    ) -> T:
        key = ProviderRouteKey.from_context(context)
        lease = await self._repository.acquire(key, owner or uuid4().hex)
        if lease.version is not None and probe is not None:
            await self._probe(lease, probe)
            # Another in-flight request may have observed a new 429 meanwhile.
            lease = await self._repository.acquire(key, lease.owner)
            if lease.version is not None:
                raise RouteCoolingDown(datetime.now(UTC) + PROBE_LEASE)
        if lease.version is not None:
            return await self._probe(lease, operation)
        try:
            return await operation(None)
        except Exception as error:
            if getattr(error, "code", None) == "provider_rate_limited":
                until = await self._repository.block(
                    key,
                    until=_limited_until(error),
                    reason_code="provider_rate_limited",
                    stable_error_code=_stable_error_code(error),
                )
                raise RouteCoolingDown(until) from error
            raise

    async def _probe[T](
        self,
        lease: ProviderRouteLease,
        operation: Callable[[datetime | None], Awaitable[T]],
    ) -> T:
        now = datetime.now(UTC)
        if lease.expires_at is None:
            raise RouteAdmissionUnavailable
        deadline = min(
            now + timedelta(seconds=PROBE_TIMEOUT_SECONDS),
            lease.expires_at - PROBE_LEASE_MARGIN,
        )
        if deadline <= now:
            # Do not renew a preclaimed lease just to start external work.
            raise RouteCoolingDown(max(now, lease.expires_at))
        try:
            async with asyncio.timeout((deadline - now).total_seconds()):
                result = await operation(deadline)
        except asyncio.CancelledError:
            # Crash/cancellation retains the lease until expiry; no early open.
            raise
        except TimeoutError as error:
            await self._repository.finish(
                lease,
                success=False,
                reason_code="probe_timeout",
                stable_error_code="inspection_timeout",
            )
            raise RouteProbeTimeout("inspection_timeout") from error
        except Exception as error:
            if getattr(error, "code", None) == "provider_rate_limited":
                until = await self._repository.block(
                    lease.key,
                    until=_limited_until(error),
                    reason_code="provider_rate_limited",
                    stable_error_code=_stable_error_code(error),
                )
                raise RouteCoolingDown(until) from error
            await self._repository.finish(
                lease,
                success=False,
                reason_code="probe_failed",
                stable_error_code=_stable_error_code(error),
            )
            raise
        await self._repository.finish(
            lease,
            success=True,
            reason_code="probe_succeeded",
        )
        return result


def _limited_until(error: Exception) -> datetime:
    # The repository applies the persistent exponential backoff. An explicit
    # Retry-After remains a lower bound and is never shortened.
    explicit = getattr(error, "retry_at", None)
    return (
        explicit
        if isinstance(explicit, datetime) and explicit.tzinfo is not None
        else datetime.now(UTC)
    )


def _stable_error_code(error: Exception) -> str:
    code = getattr(error, "code", None)
    return code if isinstance(code, str) else "inspection_failed"
