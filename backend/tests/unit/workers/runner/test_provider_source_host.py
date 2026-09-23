from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
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
    start_detached_source_service,
    write_status,
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
    now[0] += timedelta(minutes=16)
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row.revision == first.revision + 2
    assert sources.row.valid_until == now[0] + timedelta(minutes=15)
    rotated_payload = PAYLOAD.replace(b"fixture-only", b"rotated-fixture")
    selected[0] = ("candidate", rotated_payload)
    assert await sync.sync(PROVIDER) == "ready"
    assert sources.row.revision == first.revision + 3
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
    assert sources.row.revision == first.revision + 4
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


def test_host_status_is_private_and_contains_only_nonsecret_state(
    tmp_path: Path,
) -> None:
    path = tmp_path.resolve() / "runtime" / "status.json"
    write_status(
        path,
        {"youtube": "browser_permission_denied"},
        checked_at=datetime(2026, 9, 23, tzinfo=UTC),
        pid=42,
    )
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {
        "checked_at": "2026-09-23T00:00:00+00:00",
        "pid": 42,
        "states": {"youtube": "browser_permission_denied"},
    }


def test_detached_source_service_requires_fresh_child_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path.resolve()
    status = root / "runtime" / "status.json"
    pid_file = status.with_name("pid.json")
    lock_file = status.with_name("start.lock")
    commands: list[tuple[list[str], dict[str, object]]] = []

    class Child:
        pid = 4242

        def poll(self) -> None:
            return None

    def popen(command: list[str], **kwargs: object) -> Child:
        commands.append((command, kwargs))
        return Child()

    monkeypatch.setattr(
        "app.workers.runner.provider_source_host.sys.platform", "darwin"
    )
    monkeypatch.setattr("app.workers.runner.provider_source_host.STATUS_PATH", status)
    monkeypatch.setattr("app.workers.runner.provider_source_host.PID_PATH", pid_file)
    monkeypatch.setattr(
        "app.workers.runner.provider_source_host.START_LOCK_PATH", lock_file
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_source_host._owned_detached_pid", lambda: None
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_source_host.subprocess.Popen", popen
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_source_host.read_private_json",
        lambda _path, **_kwargs: {"pid": 4242, "states": {"youtube": "ready"}},
    )

    assert start_detached_source_service(
        env_file=root / "deploy.env",
        runtime_env=root / "runtime.env",
        providers=(PROVIDER,),
    ) == {"youtube": "ready"}
    assert commands[0][1]["start_new_session"] is True
    assert "--provider" in commands[0][0]
    assert stat.S_IMODE(pid_file.stat().st_mode) == 0o600
