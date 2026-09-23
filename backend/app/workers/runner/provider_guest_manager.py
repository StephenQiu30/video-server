"""Maintain public guest state and publish short, read-only execution leases."""

import argparse
import asyncio
import fcntl
import json
import os
import signal
import socket
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import get_settings_for_role
from app.core.db import create_engine, create_session_factory
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.integrations.provider_guest_bootstrap import PublicGuestBootstrap
from app.repositories.errors import LeaseConflict
from app.repositories.providers.guest_contexts import GuestContexts
from app.services.provider_guest import GuestContext, GuestScope
from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import (
    ensure_private_directory,
    no_follow_flag,
    validate_private_file,
)
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.guest_material import (
    publish_guest_lease,
    read_guest_lease,
    validate_guest_material,
)
from app.workers.runner.provider_registry import provider_profile_for_key
from app.workers.runner.settings import ProviderEgressSettings


class GuestManager:
    def __init__(
        self,
        repository: GuestContexts,
        cipher: ProviderSessionCipher,
        bootstrap: PublicGuestBootstrap,
        scope: GuestScope,
        root: Path,
        *,
        owner: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._repository, self._cipher, self._bootstrap = repository, cipher, bootstrap
        self._scope, self._root, self._owner, self._clock = scope, root, owner, clock

    async def tick(self) -> str:
        ensure_private_directory(self._root)
        fd = os.open(
            self._root / ".publish.lock",
            os.O_CREAT | os.O_RDWR | no_follow_flag(),
            0o600,
        )
        try:
            validate_private_file(fd, "unsafe guest publisher lock")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "busy"
            # Includes database connection/lock waits, not only upstream HTTP.
            async with asyncio.timeout(25):
                return await self._maintain()
        finally:
            os.close(fd)

    async def _maintain(self) -> str:
        now = self._clock()
        await self._repository.recover(now=now)
        lease = await self._repository.claim(self._scope, self._owner, now=now)
        if lease is not None:
            try:
                async with asyncio.timeout(
                    max(0, (lease.deadline - self._clock()).total_seconds())
                ):
                    payload, expiry = await self._bootstrap.prepare(
                        self._scope, now=self._clock()
                    )
                    payload = validate_guest_material(
                        self._scope, payload, now=self._clock()
                    )
                    encrypted = self._cipher.encrypt_guest(
                        self._scope, lease.revision, expiry, payload
                    )
                    await self._repository.publish(
                        lease, encrypted, now=self._clock(), valid_until=expiry
                    )
            except (RunnerFailure, TimeoutError, ValueError) as exc:
                code = (
                    exc.code
                    if isinstance(exc, RunnerFailure)
                    else "provider_temporarily_unavailable"
                )
                if code == "guest_context_required":
                    code = "provider_guest_context_required"
                if code not in {
                    "provider_rate_limited",
                    "provider_verification_required",
                    "provider_guest_context_required",
                    "provider_configuration_missing",
                    "provider_temporarily_unavailable",
                }:
                    code = "provider_temporarily_unavailable"
                try:
                    await self._repository.fail(lease, code, now=self._clock())
                except LeaseConflict:
                    pass
            except LeaseConflict:
                pass
        # Re-read after publication/failure: never replicate a stale pre-refresh
        # snapshot, and never extend the original material's validity.
        current = await self._repository.read(self._scope)
        now = self._clock()
        target = self._root / "cookies.txt"
        if current is None or not current.usable(now):
            target.unlink(missing_ok=True)
            return "unavailable" if current is None else current.state
        assert current.valid_until is not None and current.ciphertext is not None
        try:
            payload = self._cipher.decrypt_guest(
                self._scope, current.revision, current.valid_until, current.ciphertext
            )
            publish_guest_lease(
                target,
                self._scope,
                current.revision,
                payload,
                now=now,
                deadline=min(current.valid_until, now + timedelta(seconds=90)),
            )
        except (ValueError, RunnerFailure):
            target.unlink(missing_ok=True)
            await self._repository.invalidate(current, now=now)
            return "invalid"
        return "ready"


async def serve() -> None:
    settings = get_settings_for_role("provider-guest")
    runtime = ProviderEgressSettings()
    provider = ProviderKey.DOUYIN
    profile = provider_profile_for_key(provider)
    scope = _scope(provider, profile.version, profile.client_profile_id, runtime)
    engine = create_engine(settings.database_url)
    manager = GuestManager(
        GuestContexts(create_session_factory(engine)),
        ProviderSessionCipher(settings.url_encryption_key.get_secret_value()),
        PublicGuestBootstrap(runtime.egress_proxy_for(provider)),
        scope,
        settings.provider_source_root / provider.value,
        owner=f"guest-{socket.gethostname()[:64]}-{os.getpid()}",
        clock=lambda: datetime.now(UTC),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    try:
        while not stop.is_set():
            try:
                await manager.tick()
                Path("/tmp/provider-guest-heartbeat").write_text(
                    str(datetime.now(UTC).timestamp())
                )
            except Exception:
                # No upstream response, Cookie, URL or database credentials in logs.
                print("guest maintenance unavailable", flush=True)
            try:
                await asyncio.wait_for(stop.wait(), 5)
            except TimeoutError:
                pass
    finally:
        await engine.dispose()


def _scope(
    provider: ProviderKey,
    profile_version: str,
    client_profile_id: str,
    runtime: ProviderEgressSettings,
) -> GuestScope:
    return GuestScope(
        provider,
        profile_version,
        client_profile_id,
        runtime.egress_affinity_for(provider),
    )


def guest_status_document(
    context: GuestContext | None,
    scope: GuestScope,
    lease_path: Path,
    *,
    now: datetime,
) -> dict[str, str | bool | None]:
    """Operational state only; never include the encrypted or published material."""
    stored_usable = context.usable(now) if context is not None else False
    published_lease_usable = False
    if stored_usable and context is not None:
        try:
            published_lease_usable = (
                read_guest_lease(lease_path, scope, now=now).revision
                == context.revision
            )
        except RunnerFailure:
            pass
    return {
        "provider_key": ProviderKey.DOUYIN.value,
        "state": context.state if context is not None else "absent",
        "stored_usable": stored_usable,
        "published_lease_usable": published_lease_usable,
        "reason_code": context.reason_code if context is not None else None,
        "retry_at": (
            context.retry_at.isoformat()
            if context is not None and context.retry_at is not None
            else None
        ),
        "valid_until": (
            context.valid_until.isoformat()
            if context is not None and context.valid_until is not None
            else None
        ),
    }


async def diagnose() -> int:
    settings = get_settings_for_role("provider-guest")
    runtime = ProviderEgressSettings()
    provider = ProviderKey.DOUYIN
    profile = provider_profile_for_key(provider)
    scope = _scope(provider, profile.version, profile.client_profile_id, runtime)
    engine = create_engine(settings.database_url)
    try:
        context = await GuestContexts(create_session_factory(engine)).read(scope)
        document = guest_status_document(
            context,
            scope,
            settings.provider_source_root / provider.value / "cookies.txt",
            now=datetime.now(UTC),
        )
    finally:
        await engine.dispose()
    print(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    return 0 if document["published_lease_usable"] else 4


def main() -> int:
    parser = argparse.ArgumentParser(description="访客维护与脱敏状态诊断")
    parser.add_argument(
        "command", nargs="?", choices=("serve", "status"), default="serve"
    )
    args = parser.parse_args()
    if args.command == "status":
        return asyncio.run(diagnose())
    asyncio.run(serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
