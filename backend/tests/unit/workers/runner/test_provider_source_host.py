from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.db import create_session_factory
from app.core.security.provider_session_cipher import ProviderSessionCipher
from app.repositories.providers.session_sources import ProviderSessionSources
from app.services.provider_types import ProviderKey, ProviderSessionVersion
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.workers.runner.provider_source_host import (
    SOURCE_OWNER_HEADER,
    HostBrowserSourceSync,
    load_settings,
    select_source,
)
from app.workers.runner.provider_source_replica import ProviderSourceReplica
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncEngine

PROVIDER = ProviderKey.YOUTUBE
PAYLOAD = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-only\n"
)


@dataclass
class Row:
    revision: int
    ciphertext: bytes | None
    valid_until: datetime | None


class Sources:
    def __init__(self) -> None:
        self.row: Row | None = None

    async def read(self, _provider: ProviderKey) -> Row | None:
        return self.row

    async def publish(
        self,
        _provider: ProviderKey,
        *,
        expected_revision: int,
        ciphertext: bytes | None,
        valid_until: datetime | None,
    ) -> int:
        assert expected_revision == (self.row.revision if self.row else 0)
        self.row = Row(expected_revision + 1, ciphertext, valid_until)
        return self.row.revision


def test_discovery_requires_one_usable_browser_profile(tmp_path: Path) -> None:
    (tmp_path / "Default").mkdir()
    (tmp_path / "Profile 1").mkdir()

    def export(**kwargs):
        if kwargs["profile"] == "Default":
            return ProviderCookieLease(ProviderCookieLeaseStatus.OK, PAYLOAD)
        return ProviderCookieLease(ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED)

    assert select_source(PROVIDER, root=tmp_path, export=export) == (
        "candidate",
        PAYLOAD,
    )

    def both(**_kwargs):
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, PAYLOAD)

    assert select_source(PROVIDER, root=tmp_path, export=both) == (
        "browser_source_ambiguous",
        None,
    )


def test_host_settings_use_private_runtime_key_without_loading_route_json(
    tmp_path: Path,
) -> None:
    env = tmp_path / "deploy.env"
    runtime = tmp_path / "runtime.env"
    key = Fernet.generate_key().decode()
    env.write_text("DATABASE_URL=postgresql+asyncpg://a:b@localhost:5432/c\n")
    runtime.write_text(
        'RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}\n'
        f"PROVIDER_SOURCE_ENCRYPTION_KEY={key}\n"
    )
    settings = load_settings(env, runtime)
    assert settings.database_url.endswith("/c")
    assert settings.provider_source_encryption_key is not None
    assert settings.provider_source_encryption_key.get_secret_value() == key


async def test_owned_source_refresh_and_logout_are_versioned() -> None:
    sources = Sources()
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    selected = [("candidate", PAYLOAD)]
    now = [datetime(2026, 9, 23, tzinfo=UTC)]
    sync = HostBrowserSourceSync(
        sources,
        cipher,
        select=lambda _provider: selected[0],
        clock=lambda: now[0],
    )  # type: ignore[arg-type]
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row is not None
    first = sources.row
    assert first.valid_until is not None and first.ciphertext is not None
    decrypted = cipher.decrypt(
        PROVIDER, first.revision, first.valid_until, first.ciphertext
    )
    assert SOURCE_OWNER_HEADER in decrypted
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row.revision == first.revision
    now[0] += timedelta(minutes=11)
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row.revision == first.revision + 1
    assert sources.row.valid_until == now[0] + timedelta(minutes=15)
    rotated_payload = PAYLOAD.replace(b"fixture-only", b"rotated-fixture")
    selected[0] = ("candidate", rotated_payload)
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row.revision == first.revision + 2
    assert sources.row.ciphertext is not None
    assert sources.row.valid_until is not None
    assert b"rotated-fixture" in cipher.decrypt(
        PROVIDER,
        sources.row.revision,
        sources.row.valid_until,
        sources.row.ciphertext,
    )
    selected[0] = ("browser_login_missing", None)
    assert await sync.sync(PROVIDER) == "browser_login_missing"
    assert sources.row.revision == first.revision + 3
    assert sources.row.ciphertext is None


async def test_manual_source_is_preserved() -> None:
    sources = Sources()
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    expiry = datetime.now(UTC) + timedelta(hours=1)
    sources.row = Row(1, cipher.encrypt(PROVIDER, 1, expiry, PAYLOAD), expiry)
    sync = HostBrowserSourceSync(
        sources,
        cipher,
        select=lambda _provider: ("browser_login_missing", None),
    )  # type: ignore[arg-type]
    assert await sync.sync(PROVIDER) == "manual_source_preserved"
    assert sources.row.revision == 1


async def test_auto_published_source_reaches_isolated_runner_lease(
    postgres_engine: AsyncEngine, tmp_path: Path
) -> None:
    sources = ProviderSessionSources(create_session_factory(postgres_engine))
    cipher = ProviderSessionCipher(Fernet.generate_key().decode())
    sync = HostBrowserSourceSync(
        sources,
        cipher,
        select=lambda _provider: ("candidate", PAYLOAD),
    )
    assert await sync.sync(PROVIDER) == "ready"
    replica = ProviderSourceReplica(sources, cipher, tmp_path)
    assert await replica.sync(PROVIDER) == "ready"
    lease = ProviderCookieFile(
        tmp_path / "youtube/cookies.txt", require_lease=True
    ).read(PROVIDER, ProviderSessionVersion.BROWSER)
    assert b"SID\tfixture-only" in lease
    assert SOURCE_OWNER_HEADER not in lease
