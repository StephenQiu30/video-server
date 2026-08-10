from __future__ import annotations

import asyncio
import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest
from app.domain.providers import ProviderAccessMode
from app.runner.errors import RunnerFailure
from app.runner.provider_sessions import ProviderSessionStore
from app.runner.settings import RunnerSettings
from pydantic import ValidationError

SECRET = "runner-shared-secret-material-at-least-32-bytes"
COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-secret\n"
)


def operator_settings(tmp_path: Path) -> RunnerSettings:
    return RunnerSettings(
        runner_hmac_secret=SECRET,
        runner_egress_proxy="http://egress-proxy:3128",
        runner_workspace_root=tmp_path / "work",
        runner_access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        runner_operator_session_versions={"youtube": "version-1"},
        runner_operator_account_baseline_attested=True,
        runner_provider_secret_root=tmp_path / "secrets",
        runner_provider_secret_temp_root=tmp_path / "session-tmp",
        runner_max_active_tasks=1,
    )


def write_cookie(settings: RunnerSettings, payload: bytes = COOKIE) -> Path:
    source = settings.runner_provider_secret_root / "youtube" / "version-1.cookies.txt"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    os.chmod(source, 0o400)
    return source


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"runner_operator_session_versions": {"youtube": "version-1"}},
            "anonymous runner cannot configure provider sessions",
        ),
        (
            {
                "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
                "runner_operator_session_versions": {"youtube": "version-1"},
                "runner_max_active_tasks": 1,
            },
            "operator account baseline must be attested",
        ),
        (
            {
                "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
                "runner_operator_session_versions": {"youtube": "version-1"},
                "runner_operator_account_baseline_attested": True,
            },
            "operator runner concurrency must be one",
        ),
        (
            {"runner_youtube_pot_base_url": "http://youtube-pot-provider:4416"},
            "POT provider is restricted to the operator runner",
        ),
    ],
)
def test_settings_fail_closed_for_invalid_session_boundaries(
    tmp_path: Path,
    overrides: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "runner_hmac_secret": SECRET,
        "runner_egress_proxy": "http://egress-proxy:3128",
        "runner_workspace_root": tmp_path / "work",
        "runner_provider_secret_temp_root": tmp_path / "session-tmp",
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=message):
        RunnerSettings(**values)


def test_settings_reject_session_temp_inside_shared_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot be in the workspace"):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy="http://egress-proxy:3128",
            runner_workspace_root=tmp_path / "work",
            runner_provider_secret_temp_root=tmp_path / "work" / "sessions",
        )


async def test_operation_uses_unique_0600_copy_and_preserves_source(
    tmp_path: Path,
) -> None:
    settings = operator_settings(tmp_path)
    source = write_cookie(settings)
    original_stat = source.stat()
    store = ProviderSessionStore(settings)
    context = store.context_for("https://www.youtube.com/watch?v=owned")

    async with store.operation(context) as jar:
        assert jar is not None
        first_path = jar
        assert jar.parent.parent == settings.runner_provider_secret_temp_root
        if os.name == "posix":
            assert stat.S_IMODE(jar.stat().st_mode) == 0o600
            assert stat.S_IMODE(jar.parent.stat().st_mode) == 0o700
        jar.write_bytes(COOKIE + b"# operation-only\n")

    assert not first_path.exists()
    assert list(settings.runner_provider_secret_temp_root.iterdir()) == []
    assert source.read_bytes() == COOKIE
    assert source.stat().st_mtime_ns == original_stat.st_mtime_ns


async def test_failure_and_concurrent_operations_cleanup_and_isolate(
    tmp_path: Path,
) -> None:
    settings = operator_settings(tmp_path)
    write_cookie(settings)
    store = ProviderSessionStore(settings)
    context = store.context_for("https://youtu.be/owned")
    seen: list[tuple[Path, int]] = []

    async def use_then_fail() -> None:
        async with store.operation(context) as jar:
            assert jar is not None
            seen.append((jar, jar.stat().st_ino))
            await asyncio.sleep(0)
            if len(seen) == 1:
                raise RuntimeError("controlled failure")

    results = await asyncio.gather(
        use_then_fail(),
        use_then_fail(),
        return_exceptions=True,
    )

    assert any(isinstance(item, RuntimeError) for item in results)
    assert len({path for path, _ in seen}) == 2
    assert len({inode for _, inode in seen}) == 2
    assert list(settings.runner_provider_secret_temp_root.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    [
        b"not a cookie jar",
        b"# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tSID\tx\n",
        b"# Netscape HTTP Cookie File\n",
    ],
)
def test_rejects_invalid_cookie_sources(tmp_path: Path, payload: bytes) -> None:
    settings = operator_settings(tmp_path)
    write_cookie(settings, payload)

    with pytest.raises(RunnerFailure) as caught:
        ProviderSessionStore(settings)

    assert caught.value.code == "credential_rejected"


def test_rejects_symlink_cookie_source(tmp_path: Path) -> None:
    settings = operator_settings(tmp_path)
    target = tmp_path / "target.cookies.txt"
    target.write_bytes(COOKIE)
    source = settings.runner_provider_secret_root / "youtube" / "version-1.cookies.txt"
    source.parent.mkdir(parents=True)
    source.symlink_to(target)

    with pytest.raises(RunnerFailure) as caught:
        ProviderSessionStore(settings)

    assert caught.value.code == "credential_rejected"


def test_operator_context_cannot_cross_provider(tmp_path: Path) -> None:
    settings = operator_settings(tmp_path)
    write_cookie(settings)
    store = ProviderSessionStore(settings)

    with pytest.raises(RunnerFailure) as caught:
        store.context_for("https://www.bilibili.com/video/BV1xx")

    assert caught.value.code == "provider_session_not_allowed"


async def test_retained_version_can_finish_but_unlisted_version_is_revoked(
    tmp_path: Path,
) -> None:
    settings = operator_settings(tmp_path).model_copy(
        update={"runner_operator_retained_session_versions": {"youtube": ["version-0"]}}
    )
    write_cookie(settings)
    retired = settings.runner_provider_secret_root / "youtube/version-0.cookies.txt"
    retired.write_bytes(COOKIE.replace(b"fixture-secret", b"retained-secret"))
    store = ProviderSessionStore(settings)
    active = store.context_for("https://youtu.be/owned")
    retained = replace(active, credential_version_id="version-0")

    assert store.validate_context("https://youtu.be/owned", retained) == retained
    async with store.operation(retained) as jar:
        assert jar is not None
        assert b"retained-secret" in jar.read_bytes()

    revoked = replace(active, credential_version_id="version-revoked")
    with pytest.raises(RunnerFailure) as caught:
        store.validate_context("https://youtu.be/owned", revoked)
    assert caught.value.code == "credential_revoked"
