from __future__ import annotations

import asyncio
import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest
from app.domain.providers import (
    ProviderAccessMode,
    ProviderKey,
    ProviderSessionVersion,
)
from app.runner import provider_session_files
from app.runner.errors import RunnerFailure
from app.runner.provider_sessions import ProviderSessionStore
from app.runner.settings import RunnerSettings
from pydantic import ValidationError

SECRET = "runner-shared-secret-material-at-least-32-bytes"
COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-secret\n"
)


class FakeCookieSync:
    def __init__(self, *, ready: bool = True, payload: bytes = COOKIE) -> None:
        self.ready = ready
        self.payload = payload
        self.calls = 0

    def is_ready(self, provider: ProviderKey, version: ProviderSessionVersion) -> bool:
        assert provider is ProviderKey.YOUTUBE
        assert version is ProviderSessionVersion.BROWSER
        return self.ready

    async def sync(
        self, provider: ProviderKey, version: ProviderSessionVersion
    ) -> bytes:
        assert provider is ProviderKey.YOUTUBE
        assert version is ProviderSessionVersion.BROWSER
        self.calls += 1
        return self.payload


def operator_settings(tmp_path: Path) -> RunnerSettings:
    return RunnerSettings(
        runner_hmac_secret=SECRET,
        runner_egress_proxy="http://egress-proxy:3128",
        runner_workspace_root=tmp_path / "work",
        runner_access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        runner_operator_session_versions={"youtube": "browser"},
        runner_operator_account_baseline_attested=True,
        runner_provider_session_temp_root=tmp_path / "session-tmp",
        runner_provider_cookie_sync_root=tmp_path / "bridge",
        runner_max_active_tasks=1,
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"runner_operator_session_versions": {"youtube": "browser"}},
            "anonymous runner cannot configure provider sessions",
        ),
        (
            {
                "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
                "runner_operator_session_versions": {"youtube": "browser"},
                "runner_max_active_tasks": 1,
            },
            "operator account baseline must be attested",
        ),
        (
            {
                "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
                "runner_operator_session_versions": {"youtube": "browser"},
                "runner_operator_account_baseline_attested": True,
            },
            "operator runner concurrency must be one",
        ),
        (
            {
                "runner_access_mode": ProviderAccessMode.OPERATOR_MANAGED,
                "runner_operator_session_versions": {"bilibili": "browser"},
                "runner_operator_account_baseline_attested": True,
                "runner_max_active_tasks": 1,
            },
            "operator provider is not allowlisted",
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
        "runner_provider_session_temp_root": tmp_path / "session-tmp",
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=message):
        RunnerSettings(**values)


def test_operator_without_cookie_agent_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires provider Cookie sync"):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy="http://egress-proxy:3128",
            runner_workspace_root=tmp_path / "work",
            runner_access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            runner_operator_session_versions={"x": "browser"},
            runner_operator_account_baseline_attested=True,
            runner_provider_session_temp_root=tmp_path / "session-tmp",
            runner_max_active_tasks=1,
        )


def test_settings_reject_session_tmpfs_inside_shared_workspace(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="cannot be in the workspace"):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy="http://egress-proxy:3128",
            runner_workspace_root=tmp_path / "work",
            runner_provider_session_temp_root=tmp_path / "work" / "sessions",
        )


def test_operator_session_root_must_be_memory_backed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "memory session"
    root.mkdir()
    mountinfo = tmp_path / "mountinfo"
    escaped = str(root).replace(" ", r"\040")
    mountinfo.write_text(
        f"41 31 0:38 / {escaped} rw,nosuid - tmpfs tmpfs rw\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(provider_session_files.sys, "platform", "linux")

    provider_session_files.require_memory_backed_root(root, mountinfo=mountinfo)

    mountinfo.write_text(
        f"41 31 0:38 / {escaped} rw - ext4 /dev/disk rw\n",
        encoding="utf-8",
    )
    with pytest.raises(RunnerFailure) as caught:
        provider_session_files.require_memory_backed_root(root, mountinfo=mountinfo)

    assert caught.value.code == "provider_session_unavailable"


async def test_operation_uses_unique_0600_tmpfs_file_and_deletes_it(
    tmp_path: Path,
) -> None:
    settings = operator_settings(tmp_path)
    cookie_sync = FakeCookieSync()
    store = ProviderSessionStore(
        settings,
        cookie_sync=cookie_sync,
        enforce_memory_backing=False,
    )
    context = store.context_for("https://www.youtube.com/watch?v=owned")

    async with store.operation(context) as jar:
        assert jar is not None
        operation_path = jar
        assert jar.parent.parent == settings.runner_provider_session_temp_root
        assert jar.read_bytes() == COOKIE
        if os.name == "posix":
            assert stat.S_IMODE(jar.stat().st_mode) == 0o600
            assert stat.S_IMODE(jar.parent.stat().st_mode) == 0o700

    assert cookie_sync.calls == 1
    assert not operation_path.exists()
    assert list(settings.runner_provider_session_temp_root.iterdir()) == []


async def test_failure_and_concurrent_operations_cleanup_and_isolate(
    tmp_path: Path,
) -> None:
    settings = operator_settings(tmp_path)
    store = ProviderSessionStore(
        settings,
        cookie_sync=FakeCookieSync(),
        enforce_memory_backing=False,
    )
    context = store.context_for("https://youtu.be/owned")
    seen: list[Path] = []

    async def use_then_fail() -> None:
        async with store.operation(context) as jar:
            assert jar is not None
            seen.append(jar)
            await asyncio.sleep(0)
            if len(seen) == 1:
                raise RuntimeError("controlled failure")

    results = await asyncio.gather(
        use_then_fail(),
        use_then_fail(),
        return_exceptions=True,
    )

    assert any(isinstance(item, RuntimeError) for item in results)
    assert len(set(seen)) == 2
    assert list(settings.runner_provider_session_temp_root.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    [
        b"not a cookie jar",
        b"# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tSID\tx\n",
        b"# Netscape HTTP Cookie File\n",
    ],
)
async def test_rejects_invalid_in_memory_leases(tmp_path: Path, payload: bytes) -> None:
    settings = operator_settings(tmp_path)
    store = ProviderSessionStore(
        settings,
        cookie_sync=FakeCookieSync(payload=payload),
        enforce_memory_backing=False,
    )
    context = store.context_for("https://youtu.be/owned")

    with pytest.raises(RunnerFailure) as caught:
        async with store.operation(context):
            pass

    assert caught.value.code == "credential_rejected"
    assert list(settings.runner_provider_session_temp_root.iterdir()) == []


def test_operator_context_cannot_cross_provider(tmp_path: Path) -> None:
    store = ProviderSessionStore(
        operator_settings(tmp_path),
        cookie_sync=FakeCookieSync(),
        enforce_memory_backing=False,
    )

    with pytest.raises(RunnerFailure) as caught:
        store.context_for("https://www.bilibili.com/video/BV1xx")

    assert caught.value.code == "provider_session_not_allowed"


def test_non_current_session_source_is_revoked(tmp_path: Path) -> None:
    store = ProviderSessionStore(
        operator_settings(tmp_path),
        cookie_sync=FakeCookieSync(),
        enforce_memory_backing=False,
    )
    active = store.context_for("https://youtu.be/owned")
    previous = replace(active, credential_version_id="previous")

    with pytest.raises(RunnerFailure) as caught:
        store.validate_context("https://youtu.be/owned", previous)

    assert caught.value.code == "credential_revoked"


def test_live_agent_readiness_does_not_export_a_session(tmp_path: Path) -> None:
    cookie_sync = FakeCookieSync()
    store = ProviderSessionStore(
        operator_settings(tmp_path),
        cookie_sync=cookie_sync,
        enforce_memory_backing=False,
    )

    assert store.is_ready() is True
    assert cookie_sync.calls == 0


def test_live_agent_readiness_fails_when_bridge_is_unavailable(
    tmp_path: Path,
) -> None:
    store = ProviderSessionStore(
        operator_settings(tmp_path),
        cookie_sync=FakeCookieSync(ready=False),
        enforce_memory_backing=False,
    )

    assert store.is_ready() is False
