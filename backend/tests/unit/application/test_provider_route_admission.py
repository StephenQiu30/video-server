import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.domain.providers import ProviderAccessMode
from app.integrations.media_runner_models import MediaRunnerClientError
from app.services.provider_route_admission import (
    ProviderRouteAdmission,
    ProviderRouteKey,
    ProviderRouteLease,
    RouteCoolingDown,
    RouteProbeTimeout,
)
from tests.unit.infrastructure.test_media_runner_router import context


class Cooldowns:
    def __init__(self, *, half_open=False):
        self.version = 1 if half_open else None
        self.blocked = False
        self.finished = []

    async def acquire(self, key, owner):
        if self.blocked:
            raise RouteCoolingDown(datetime.now(UTC) + timedelta(minutes=5))
        return ProviderRouteLease(
            key, owner, self.version, datetime.now(UTC) + timedelta(seconds=60)
        )

    async def block(self, key, *, until):
        self.blocked = True
        return until

    async def finish(self, lease, *, success):
        self.finished.append(success)
        self.blocked = not success
        self.version = None


async def test_429_blocks_the_next_operation_without_executing_it():
    repo = Cooldowns()
    admission = ProviderRouteAdmission(repo)
    calls = 0

    async def limited(deadline):
        nonlocal calls
        calls += 1
        raise MediaRunnerClientError("provider_rate_limited", 429)

    for _ in range(2):
        with pytest.raises(RouteCoolingDown):
            await admission.run(context(ProviderAccessMode.ANONYMOUS), limited)
    assert calls == 1


async def test_half_open_download_requires_one_light_probe_before_media():
    repo = Cooldowns(half_open=True)
    events = []

    async def probe(deadline):
        assert deadline is not None
        events.append("metadata")

    async def download(deadline):
        assert deadline is None
        events.append("media")
        return "artifact"

    result = await ProviderRouteAdmission(repo).run(
        context(ProviderAccessMode.ANONYMOUS),
        download,
        probe=probe,
    )
    assert result == "artifact"
    assert events == ["metadata", "media"]
    assert repo.finished == [True]


async def test_cancelled_probe_retains_lease_without_opening_route():
    repo = Cooldowns(half_open=True)
    started = asyncio.Event()

    async def blocked(deadline):
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        ProviderRouteAdmission(repo).run(
            context(ProviderAccessMode.ANONYMOUS),
            blocked,
        )
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert repo.finished == []
    assert repo.version == 1


async def test_probe_timeout_fails_closed_with_stable_classification(monkeypatch):
    monkeypatch.setattr(
        "app.services.provider_route_admission.PROBE_TIMEOUT_SECONDS", 0.01
    )
    repo = Cooldowns(half_open=True)

    async def never(deadline):
        await asyncio.Event().wait()

    with pytest.raises(RouteProbeTimeout):
        await ProviderRouteAdmission(repo).run(
            context(ProviderAccessMode.ANONYMOUS), never
        )
    assert repo.finished == [False]


def test_cookie_and_engine_changes_do_not_reset_the_route_key():
    original = context(ProviderAccessMode.OPERATOR_MANAGED)
    changed = replace(
        original, credential_version_id="new-cookie", engine_commit="new-engine"
    )
    assert ProviderRouteKey.from_context(original) == ProviderRouteKey.from_context(
        changed
    )


async def test_expiring_preclaimed_lease_never_starts_external_probe():
    class Expiring(Cooldowns):
        async def acquire(self, key, owner):
            return ProviderRouteLease(
                key, owner, 1, datetime.now(UTC) + timedelta(seconds=1)
            )

    called = False

    async def operation(deadline=None):
        nonlocal called
        called = True

    with pytest.raises(RouteCoolingDown):
        await ProviderRouteAdmission(Expiring()).run(
            context(ProviderAccessMode.ANONYMOUS), operation
        )
    assert called is False


async def test_probe_deadline_is_clamped_to_persisted_lease_not_reset():
    expires = datetime.now(UTC) + timedelta(seconds=8)

    class ShortLease(Cooldowns):
        async def acquire(self, key, owner):
            return ProviderRouteLease(key, owner, 1, expires)

    async def operation(deadline):
        assert deadline == expires - timedelta(seconds=5)
        return "metadata"

    assert (
        await ProviderRouteAdmission(ShortLease()).run(
            context(ProviderAccessMode.ANONYMOUS), operation
        )
        == "metadata"
    )
