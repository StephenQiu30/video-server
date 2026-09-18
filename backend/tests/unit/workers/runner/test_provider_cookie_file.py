from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from app.services.provider_types import (
    ProviderAccessMode,
    ProviderKey,
    ProviderSessionVersion,
)
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_sessions import ProviderSessionStore
from app.workers.runner.settings import RunnerSettings
from pydantic import ValidationError

COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-only\n"
)


def cookie_file(root: Path, payload: bytes = COOKIE) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "cookies.txt"
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


def settings(root: Path, path: Path, **overrides: object) -> RunnerSettings:
    values: dict[str, object] = {
        "runner_hmac_secret": "test-runner-secret-with-at-least-32-bytes",
        "runner_egress_proxy": "http://egress-proxy:3128",
        "runner_workspace_root": root / "work",
        "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
        "runner_operator_session_versions": {"youtube": "browser"},
        "runner_operator_account_baseline_attested": True,
        "runner_provider_session_temp_root": root / "tmp",
        "runner_provider_cookie_file": path,
        "runner_max_active_tasks": 1,
    }
    values.update(overrides)
    return RunnerSettings(**values)


async def test_restart_and_machine_move_preserve_session_without_agent(
    tmp_path: Path,
) -> None:
    source = cookie_file(tmp_path / "machine-a" / "source")
    store = ProviderSessionStore(
        settings(tmp_path / "machine-a", source), enforce_memory_backing=False
    )
    context = store.context_for("https://youtu.be/owned")
    assert await store.is_ready()
    async with store.operation(context) as jar:
        assert jar is not None
        assert jar.read_bytes() == COOKIE
        jar.write_bytes(b"temporary Set-Cookie update")
    assert source.read_bytes() == COOKIE
    assert not jar.exists()

    # A fresh machine retains only the source and settings, never the temp jar.
    destination = cookie_file(tmp_path / "machine-b" / "source")
    shutil.copyfile(source, destination)
    restarted = ProviderSessionStore(
        settings(tmp_path / "machine-b", destination), enforce_memory_backing=False
    )
    assert await restarted.is_ready()
    assert restarted.context_for("https://youtu.be/owned") == context
    async with restarted.operation(context) as restored:
        assert restored is not None
        assert restored.read_bytes() == COOKIE


async def test_rotation_fences_old_context_and_new_operation_reads_replacement(
    tmp_path: Path,
) -> None:
    source = cookie_file(tmp_path / "source")
    store = ProviderSessionStore(
        settings(tmp_path, source), enforce_memory_backing=False
    )
    old = store.context_for("https://youtu.be/owned")
    replacement = cookie_file(
        tmp_path / "replacement", COOKIE.replace(b"fixture-only", b"new-fixture")
    )
    os.replace(replacement, source)
    with pytest.raises(RunnerFailure, match="credential revoked"):
        async with store.operation(old):
            pytest.fail("old inspection cannot silently use a new account")
    current = store.context_for("https://youtu.be/owned")
    assert current.credential_version_id != old.credential_version_id
    async with store.operation(current) as jar:
        assert jar is not None
        assert b"new-fixture" in jar.read_bytes()


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"not Netscape",
        COOKIE.replace(b"youtube.com", b"example.com"),
        COOKIE.replace(b"2147483647", b"yesterday"),
        COOKIE.replace(b"TRUE", b"invalid"),
        COOKIE.replace(b"SID", b"\x00SID"),
        COOKIE + b"x" * 1024**2,
    ],
)
def test_rejects_malformed_or_cross_provider_files(
    tmp_path: Path, payload: bytes
) -> None:
    source = ProviderCookieFile(cookie_file(tmp_path, payload))
    with pytest.raises(RunnerFailure) as caught:
        source.read(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    assert caught.value.code == "credential_rejected"


async def test_expired_and_missing_credentials_are_not_ready_and_can_recover(
    tmp_path: Path,
) -> None:
    path = cookie_file(tmp_path, COOKIE.replace(b"2147483647", b"1"))
    source = ProviderCookieFile(path)
    assert not await source.is_ready(
        ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER
    )
    with pytest.raises(RunnerFailure, match="credential expired"):
        await source.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    path.unlink()
    with pytest.raises(RunnerFailure, match="credential required"):
        await source.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    cookie_file(tmp_path)
    assert await source.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "world-readable", "hardlink"])
def test_rejects_unsafe_source_without_blocking(tmp_path: Path, kind: str) -> None:
    path = cookie_file(tmp_path / "original")
    if kind == "symlink":
        target = tmp_path / "symlink"
        target.symlink_to(path)
        path = target
    elif kind == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    elif kind == "hardlink":
        os.link(path, tmp_path / "second-link")
    else:
        path.chmod(0o644)
    with pytest.raises(RunnerFailure):
        ProviderCookieFile(path).read(
            ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"runner_provider_cookie_sync_root": Path("/bridge")},
        {"runner_access_mode": ProviderAccessMode.ANONYMOUS},
        {"runner_operator_session_versions": {"wechat_channels": "browser"}},
    ],
)
def test_file_source_keeps_existing_isolation_rules(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        settings(tmp_path, cookie_file(tmp_path / "source"), **overrides)


def test_file_source_cannot_live_in_shared_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot be in the workspace"):
        settings(tmp_path, tmp_path / "work" / "cookies.txt")


def test_dynamic_browser_state_cannot_be_replaced_by_a_file(tmp_path: Path) -> None:
    with pytest.raises(RunnerFailure, match="provider session not allowed"):
        ProviderCookieFile(cookie_file(tmp_path)).read(
            ProviderKey.WECHAT_CHANNELS, ProviderSessionVersion.BROWSER
        )
