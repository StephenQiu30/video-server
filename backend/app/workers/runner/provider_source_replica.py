"""Publish bounded local leases from deployment-owned persistent sources.

This management process has database access. Media Runners have neither the
database URL nor the source encryption key, and mount only their own replica.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import os
import signal
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import Settings
from app.core.db import create_engine, create_session_factory
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.repositories.providers.session_sources import (
    ProviderSessionSources,
    SourceRevisionConflict,
)
from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import (
    ensure_private_directory,
    no_follow_flag,
    validate_private_file,
)
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.netscape_cookie import live_cookie_payload
from app.workers.runner.provider_cookie_file import (
    SOURCE_LEASE_PREFIX,
    ProviderCookieFile,
)
from app.workers.runner.provider_session_policy import browser_session_policy
from app.workers.runner.provider_session_setup import publish_session
from sqlalchemy.exc import SQLAlchemyError

# These deployment file routes exist in Compose. Dedicated browser sources
# (notably Yuanbao) retain their distinct authorization boundary.
FILE_PROVIDERS = (
    ProviderKey.YOUTUBE,
    ProviderKey.DOUYIN,
    ProviderKey.REDDIT,
    ProviderKey.YOUKU,
    ProviderKey.QQVIDEO,
)


class ProviderSourceReplica:
    def __init__(
        self,
        sources: ProviderSessionSources,
        cipher: ProviderSessionCipher,
        root: Path,
        *,
        lease_seconds: int = 90,
    ) -> None:
        self._sources, self._cipher, self._root = sources, cipher, root
        self._lease_seconds = lease_seconds

    async def sync(self, provider: ProviderKey) -> str:
        if provider not in FILE_PROVIDERS:
            raise ValueError("provider has no deployment file route")
        root = self._root / provider.value
        ensure_private_directory(root)
        # A single publisher per local volume prevents an old DB read from
        # overwriting a newer revocation. Different machines use separate volumes.
        lock = os.open(
            root / ".replica.lock", os.O_CREAT | os.O_RDWR | no_follow_flag(), 0o600
        )
        try:
            validate_private_file(lock, "unsafe provider replica lock")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "busy"
            async with asyncio.timeout(5):
                row = await self._sources.read(provider)
            now = datetime.now(UTC)
            if (
                row is None
                or row.ciphertext is None
                or row.valid_until is None
                or row.valid_until <= now
            ):
                (root / "cookies.txt").unlink(missing_ok=True)
                return "unavailable"
            try:
                payload = self._cipher.decrypt(
                    provider, row.revision, row.valid_until, row.ciphertext
                )
                policy = browser_session_policy(provider)
                live, names = live_cookie_payload(payload, frozenset(policy.domains))
                if not policy.accepts(names):
                    raise ValueError("source expired")
                deadline = min(
                    row.valid_until, now + timedelta(seconds=self._lease_seconds)
                )
                deadline_seconds = int(deadline.timestamp())
                lease = (
                    SOURCE_LEASE_PREFIX
                    + f"{provider.value} {row.revision} {deadline_seconds}\n".encode()
                )
                header, body = live.split(b"\n", 1)
                publish_session(provider, root, header + b"\n" + lease + body)
            except (ValueError, RunnerFailure):
                (root / "cookies.txt").unlink(missing_ok=True)
                return "invalid"
            return "ready"
        finally:
            os.close(lock)


async def serve(settings: Settings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    key = settings.provider_source_encryption_key
    engine = create_engine(settings.database_url) if key is not None else None
    replica = (
        ProviderSourceReplica(
            ProviderSessionSources(create_session_factory(engine)),
            ProviderSessionCipher(key.get_secret_value()),
            settings.provider_source_root,
            lease_seconds=settings.provider_source_lease_seconds,
        )
        if engine is not None and key is not None
        else None
    )
    previous: dict[ProviderKey, str] = {}
    if replica is None:
        print("provider sources: disabled (encryption key not configured)", flush=True)
    try:
        while not stop.is_set():
            if replica is not None:

                async def synchronize(provider: ProviderKey) -> tuple[ProviderKey, str]:
                    try:
                        return provider, await replica.sync(provider)
                    except (OSError, SQLAlchemyError, TimeoutError):
                        # Existing files expire independently inside each Runner
                        # even if the publisher is killed or DB access is lost.
                        return provider, "unavailable"

                results = await asyncio.gather(
                    *(synchronize(p) for p in FILE_PROVIDERS)
                )
                for provider, status in results:
                    if previous.get(provider) != status:
                        print(f"provider source {provider.value}: {status}", flush=True)
                        previous[provider] = status
            Path("/tmp/provider-sources-heartbeat").write_text(str(time.time()))
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=settings.provider_source_poll_seconds
                )
            except TimeoutError:
                pass
    finally:
        if engine is not None:
            await engine.dispose()


async def administer(args: argparse.Namespace, settings: Settings) -> None:
    key = settings.provider_source_encryption_key
    if key is None:
        raise ValueError("PROVIDER_SOURCE_ENCRYPTION_KEY is required")
    engine = create_engine(settings.database_url)
    try:
        sources = ProviderSessionSources(create_session_factory(engine))
        provider = ProviderKey(args.provider)
        if args.command == "status":
            row = await sources.read(provider)
            state = "missing"
            if row is not None:
                state = "revoked" if row.ciphertext is None else "registered"
                if row.valid_until and row.valid_until <= datetime.now(UTC):
                    state = "expired"
            print(
                f"{provider.value}: revision={row.revision if row else 0}; "
                f"state={state}"
            )
            return
        payload = None
        valid_until = None
        if args.command == "publish":
            valid_until = datetime.now(UTC) + timedelta(seconds=args.valid_for_seconds)
            raw = ProviderCookieFile(args.source).read(
                provider, browser_session_policy(provider).version
            )
            payload = ProviderSessionCipher(key.get_secret_value()).encrypt(
                provider, args.expected_revision + 1, valid_until, raw
            )
        revision = await sources.publish(
            provider,
            expected_revision=args.expected_revision,
            ciphertext=payload,
            valid_until=valid_until,
        )
        state = "published" if payload else "revoked"
        print(f"{provider.value}: revision={revision}; state={state}")
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="管理部署会话持久来源与自动恢复，不读取普通用户浏览器"
    )
    parser.add_argument("command", choices=("serve", "status", "publish", "revoke"))
    parser.add_argument("--provider", choices=[p.value for p in FILE_PROVIDERS])
    parser.add_argument("--source", type=Path)
    parser.add_argument("--expected-revision", type=int)
    parser.add_argument("--valid-for-seconds", type=int, default=86400)
    args = parser.parse_args()
    if args.command != "serve" and args.provider is None:
        parser.error("--provider is required")
    if args.command in {"publish", "revoke"} and (
        args.expected_revision is None or args.expected_revision < 0
    ):
        parser.error("--expected-revision is required and must be nonnegative")
    if args.command == "publish" and (
        args.source is None or not 60 <= args.valid_for_seconds <= 604800
    ):
        parser.error(
            "publish requires --source and validity between 60 and 604800 seconds"
        )
    try:
        settings = Settings(service_role="provider-sources")

        async def run() -> None:
            if args.command == "serve":
                await serve(settings)
            else:
                async with asyncio.timeout(5):
                    await administer(args, settings)

        asyncio.run(run())
    except SourceRevisionConflict:
        print("来源已被更新或撤销；请重新读取版本并确认后发布。")
        return 2
    except (ValueError, OSError, SQLAlchemyError, RunnerFailure, TimeoutError):
        print("来源操作未完成，请检查配置、密钥、来源有效性与数据库连接。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
