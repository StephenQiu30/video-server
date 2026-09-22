from __future__ import annotations

import asyncio
import plistlib
import stat
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from app.services.provider_types import (
    ProviderAuthorizationSource,
    ProviderKey,
    ProviderSessionVersion,
)
from app.workers.runner import provider_cookie_agent as agent
from app.workers.runner.provider_authorization_queue import AUTHORIZATION_READY_PAYLOAD
from app.workers.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.workers.runner.provider_cookie_queue import ProviderCookieOperation
from app.workers.runner.provider_cookie_sync import ProviderCookieSyncClient


def _result(code: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), code, "", "")


def test_launchd_definition_is_on_demand_and_platform_neutral(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(agent.sys, "executable", "/private/venv/bin/python")

    document = agent._launch_agent_plist(
        tmp_path / "runtime",
        "Default",
    )

    assert "RunAtLoad" not in document
    assert "KeepAlive" not in document
    assert document["ThrottleInterval"] == 1
    assert document["QueueDirectories"] == [
        *[
            str(tmp_path / "runtime" / provider.value / "requests")
            for provider in sorted(agent.browser_session_providers(), key=str)
        ],
        str(tmp_path / "runtime" / "control" / "requests"),
    ]
    assert document["ProgramArguments"][:4] == [
        "/private/venv/bin/python",
        "-m",
        "app.workers.runner.provider_cookie_agent",
        "run",
    ]


def test_launchd_definition_can_use_provider_isolated_browser_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(agent.sys, "executable", "/private/venv/bin/python")

    document = agent._launch_agent_plist(
        tmp_path / "runtime",
        "Default",
        browser_root=tmp_path / "browser-root",
    )

    arguments = document["ProgramArguments"]
    assert arguments[-2:] == ["--browser-root", str(tmp_path / "browser-root")]


def test_install_prepares_only_the_encrypted_runtime_and_agent_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    definition = tmp_path / "LaunchAgents" / "agent.plist"
    runtime = tmp_path / "runtime"
    actions: list[tuple[str, ...]] = []
    # Files are created by the real CI user; mocking getuid globally would
    # invalidate the production ownership checks on every non-501 host.
    uid = agent.os.getuid()
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent, "PLIST_PATH", definition)
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(113))
    native_hosts: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        agent,
        "install_native_host",
        lambda root, extension_id: native_hosts.append((root, extension_id)),
    )
    monkeypatch.setattr(
        agent.subprocess, "run", lambda command, **kwargs: actions.append(command)
    )

    agent.install_agent(runtime, profile="Default")

    document = plistlib.loads(definition.read_bytes())
    assert actions == [("launchctl", "bootstrap", f"gui/{uid}", str(definition))]
    assert native_hosts == [(runtime, "ljffjbenpehbfgjgdmgecaiimhekoeng")]
    assert "RunAtLoad" not in document
    assert stat.S_IMODE(runtime.stat().st_mode) == 0o711
    assert stat.S_IMODE(definition.stat().st_mode) == 0o600
    for provider in agent.browser_session_providers():
        provider_root = runtime / provider.value
        assert (provider_root / ".agent-installed").read_bytes() == (
            agent.AGENT_READY_PAYLOAD
        )
    assert (runtime / "control" / agent.AUTHORIZATION_READY_MARKER).read_bytes() == (
        AUTHORIZATION_READY_PAYLOAD
    )
    arguments = document["ProgramArguments"]
    assert "--secret-root" not in arguments
    assert "--state-root" not in arguments


def test_uninstall_removes_browser_snapshots_and_source_markers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.workers.runner.provider_browser_bridge_store import (
        ProviderBrowserBridgeStore,
    )

    runtime = tmp_path / "runtime"
    agent.prepare_authorization_runtime(runtime)
    agent.write_authorization_source(
        runtime,
        ProviderKey.YOUTUBE,
        ProviderAuthorizationSource.CURRENT_CHROME,
    )
    ProviderBrowserBridgeStore(runtime).write(
        ProviderKey.YOUTUBE,
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tcurrent-session\n",
    )
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent, "_stop_loaded_agent", lambda: True)
    monkeypatch.setattr(agent, "uninstall_native_host", lambda: None)
    monkeypatch.setattr(agent, "PLIST_PATH", tmp_path / "missing.plist")

    agent.uninstall_agent(runtime)

    assert not (runtime / "bridge").exists()
    assert not (runtime / agent.AUTHORIZATION_SOURCE_DIRECTORY).exists()


def test_agent_routes_each_request_to_an_in_memory_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[ProviderKey, str, ProviderSessionVersion]] = []

    def refresh(
        *,
        provider: ProviderKey,
        profile: str,
        version: ProviderSessionVersion,
    ) -> ProviderCookieLease:
        calls.append((provider, profile, version))
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"cookie")

    monkeypatch.setattr(agent, "export_provider_cookie_lease_bounded", refresh)
    monkeypatch.setattr(
        agent,
        "read_authorization_source",
        lambda *_args: ProviderAuthorizationSource.DEDICATED_CHROME,
    )

    def drain(
        _runtime: Path,
        expected: ProviderKey,
        callback: Callable[[ProviderKey, ProviderSessionVersion], ProviderCookieLease],
        _publish: object,
        **_kwargs: object,
    ) -> None:
        if (
            expected is ProviderKey.INSTAGRAM
            and _kwargs.get("operation") is ProviderCookieOperation.REFRESH
        ):
            callback(expected, ProviderSessionVersion.BROWSER)

    monkeypatch.setattr(agent, "drain_request_batch", drain)

    agent.drain_requests(
        tmp_path / "runtime",
        profile="Default",
    )

    assert calls
    assert set(calls) == {
        (
            ProviderKey.INSTAGRAM,
            "Default",
            ProviderSessionVersion.BROWSER,
        )
    }


def test_agent_uses_current_browser_bridge_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.workers.runner.provider_browser_bridge_store import (
        ProviderBrowserBridgeStore,
    )

    runtime = tmp_path / "runtime"
    ProviderBrowserBridgeStore(runtime).write(
        ProviderKey.YOUTUBE,
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tcurrent-session\n",
    )
    monkeypatch.setattr(
        agent,
        "browser_session_providers",
        lambda: frozenset({ProviderKey.YOUTUBE}),
    )
    results: list[agent.ProviderCookieLease] = []

    def drain(
        _runtime: Path,
        expected: ProviderKey,
        callback: Callable[
            [ProviderKey, ProviderSessionVersion], agent.ProviderCookieLease
        ],
        _publish: object,
        **_kwargs: object,
    ) -> None:
        if _kwargs.get("operation") is ProviderCookieOperation.REFRESH:
            results.append(callback(expected, ProviderSessionVersion.BROWSER))

    monkeypatch.setattr(agent, "drain_request_batch", drain)

    agent.drain_requests(runtime, profile="Default")

    assert len(results) == 1
    assert results[0].status is agent.ProviderCookieLeaseStatus.OK
    assert results[0].payload is not None
    assert b"current-session" in results[0].payload


def test_non_macos_commands_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent.sys, "platform", "linux")

    with pytest.raises(SystemExit, match="requires macOS"):
        agent.main(("status",))


def test_doctor_reports_only_stable_source_statuses(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(
        agent,
        "browser_session_providers",
        lambda: frozenset({ProviderKey.YOUTUBE}),
    )
    monkeypatch.setattr(
        agent,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.PERMISSION_DENIED
        ),
    )

    assert agent.main(("doctor", "--profile", "Default")) == 5
    assert capsys.readouterr().out == ("youtube: provider_session_permission_denied\n")


def test_doctor_accepts_one_provider_and_never_prints_cookie_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(
        agent,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.OK,
            b"private-cookie-payload",
        ),
    )

    assert agent.main(("doctor", "--provider", "youtube")) == 0
    output = capsys.readouterr().out
    assert output == "youtube: ok\n"
    assert "private-cookie-payload" not in output


def test_authorize_opens_a_dedicated_profile_and_waits_for_valid_cookies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        agent.subprocess,
        "run",
        lambda command, **_kwargs: actions.append(command),
    )
    leases = iter(
        (
            ProviderCookieLease(ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED),
            ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"private"),
        )
    )
    calls: list[Path] = []
    monkeypatch.setattr(
        agent,
        "export_provider_cookie_lease_bounded",
        lambda **kwargs: calls.append(kwargs["chrome_root"]) or next(leases),
    )
    clock = iter((0.0, 1.0))
    monkeypatch.setattr(agent.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(agent.time, "sleep", lambda _seconds: None)

    assert (
        agent.authorize_provider(
            ProviderKey.YOUTUBE,
            browser_root=tmp_path / "browser-root",
            wait_seconds=10,
        )
        == 0
    )

    provider_root = tmp_path / "browser-root" / "youtube"
    assert actions == [
        (
            "open",
            "-na",
            "Google Chrome",
            "--args",
            f"--user-data-dir={provider_root}",
            "--profile-directory=Default",
            "https://www.youtube.com/",
        )
    ]
    assert calls == [provider_root, provider_root]
    output = capsys.readouterr().out
    assert "authorized: youtube" in output
    assert "private-cookie-payload" not in output


async def test_agent_probe_recovers_after_no_response_without_browser_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / ProviderKey.YOUTUBE.value
    agent.prepare_runtime(root)
    agent._write_ready_marker(root)
    exports: list[object] = []

    def forbidden_export(**kwargs: object) -> ProviderCookieLease:
        exports.append(kwargs)
        raise AssertionError("health probe must not access the browser")

    monkeypatch.setattr(agent, "export_provider_cookie_lease_bounded", forbidden_export)
    client = ProviderCookieSyncClient(
        root, timeout_seconds=0.02, poll_interval_seconds=0.001
    )
    assert not await client.is_ready(
        ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER
    )

    client = ProviderCookieSyncClient(
        root, timeout_seconds=1, poll_interval_seconds=0.001
    )
    probe = asyncio.create_task(
        client.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    )
    async with asyncio.timeout(1):
        while not list((root / "requests").iterdir()):
            await asyncio.sleep(0.001)
    await asyncio.to_thread(agent.drain_requests, tmp_path, profile="Default")
    assert await probe
    assert exports == []
    assert list((root / "requests").iterdir()) == []
    assert list((root / "responses").iterdir()) == []


@pytest.mark.parametrize("operation", list(ProviderCookieOperation))
async def test_slow_provider_does_not_block_later_requests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: ProviderCookieOperation,
) -> None:
    started = threading.Event()
    arrived = threading.Event()
    served = threading.Event()
    release = threading.Event()
    monkeypatch.setattr(
        agent,
        "browser_session_providers",
        lambda: frozenset({ProviderKey.DOUYIN, ProviderKey.WECHAT_CHANNELS}),
    )

    def drain(
        _root: Path, provider: ProviderKey, *_args: object, **kwargs: object
    ) -> None:
        requested = kwargs["operation"]
        if (
            provider is ProviderKey.WECHAT_CHANNELS
            and requested is ProviderCookieOperation.REFRESH
        ):
            started.set()
            assert release.wait(3)
        if (
            provider is ProviderKey.DOUYIN
            and requested is operation
            and arrived.is_set()
        ):
            served.set()

    monkeypatch.setattr(agent, "drain_request_batch", drain)
    task = asyncio.create_task(
        asyncio.to_thread(agent.drain_requests, tmp_path, profile="Default")
    )
    try:
        assert await asyncio.to_thread(started.wait, 1)
        arrived.set()
        assert await asyncio.to_thread(served.wait, 1)
    finally:
        release.set()
        await task
