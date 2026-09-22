from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from stat import S_IMODE

import pytest
from app.services.provider_types import ProviderAuthorizationSource, ProviderKey
from app.workers.runner import provider_cookie_agent as agent
from app.workers.runner.provider_authorization_queue import (
    AUTHORIZATION_READY_MARKER,
    AUTHORIZATION_READY_PAYLOAD,
    FileProviderAuthorizationQueue,
    ProviderAuthorizationRequest,
    authorization_runtime,
    cancel_authorization,
    prepare_authorization_runtime,
    read_authorization_response,
    read_authorization_source,
    remove_authorization_response,
    write_authorization_request,
)
from app.workers.runner.provider_browser_bridge_store import ProviderBrowserBridgeStore

TOKEN = "0123456789abcdef0123456789abcdef"


def test_agent_readiness_requires_a_live_probe_response(tmp_path: Path) -> None:
    prepare_authorization_runtime(tmp_path)
    control = authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    queue = FileProviderAuthorizationQueue(tmp_path, probe_timeout_seconds=1)

    with ThreadPoolExecutor(max_workers=1) as pool:
        ready = pool.submit(queue.agent_ready, ProviderKey.YOUTUBE)
        deadline = time.monotonic() + 1
        requests = control / "requests"
        while not tuple(requests.glob("*.request")):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        agent.drain_authorization_requests(
            tmp_path,
            profile="Default",
            browser_root=tmp_path / "browser-root",
        )

        assert ready.result(timeout=1) is True


def test_default_probe_budget_allows_a_cold_launchd_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepare_authorization_runtime(tmp_path)
    control = authorization_runtime(tmp_path)
    (control / AUTHORIZATION_READY_MARKER).write_bytes(AUTHORIZATION_READY_PAYLOAD)
    clock = [0.0]
    monkeypatch.setattr(
        "app.workers.runner.provider_authorization_queue.time.monotonic",
        lambda: clock[0],
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_authorization_queue.time.sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_authorization_queue.read_authorization_response",
        lambda *_args: "agent_ready" if clock[0] >= 2.0 else None,
    )

    assert FileProviderAuthorizationQueue(tmp_path).agent_ready(ProviderKey.YOUTUBE)


def test_new_probe_is_served_while_an_authorization_waits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_authorization_runtime(tmp_path)
    waiting_token = "11111111111111111111111111111111"
    probe_token = "22222222222222222222222222222222"
    started = threading.Event()
    release = threading.Event()
    write_authorization_request(
        tmp_path,
        waiting_token,
        ProviderAuthorizationRequest(
            ProviderKey.YOUTUBE,
            datetime.now(UTC) + timedelta(minutes=5),
            ProviderAuthorizationSource.CURRENT_CHROME,
        ),
    )

    def wait_for_session(
        *_args: object, **_kwargs: object
    ) -> agent.ProviderCookieLease:
        started.set()
        assert release.wait(3)
        return agent.ProviderCookieLease(
            agent.ProviderCookieLeaseStatus.PERMISSION_DENIED
        )

    monkeypatch.setattr(agent, "_export_from_source", wait_for_session)
    monkeypatch.setattr(agent, "BROWSER_BRIDGE_HANDSHAKE_SECONDS", 0)
    with ThreadPoolExecutor(max_workers=1) as pool:
        draining = pool.submit(
            agent.drain_authorization_requests,
            tmp_path,
            profile="Default",
            browser_root=tmp_path / "browser-root",
        )
        assert started.wait(1)
        write_authorization_request(
            tmp_path,
            probe_token,
            ProviderAuthorizationRequest(
                ProviderKey.YOUTUBE,
                datetime.now(UTC) + timedelta(seconds=5),
                ProviderAuthorizationSource.CURRENT_CHROME,
                probe=True,
            ),
        )
        deadline = time.monotonic() + 1
        while read_authorization_response(tmp_path, probe_token) != "agent_ready":
            assert time.monotonic() < deadline
            time.sleep(0.01)
        release.set()
        draining.result(timeout=1)


def test_authorization_request_is_provider_scoped_and_response_is_bounded(
    tmp_path: Path,
) -> None:
    prepare_authorization_runtime(tmp_path)
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    request = ProviderAuthorizationRequest(ProviderKey.YOUTUBE, expires_at)

    write_authorization_request(
        tmp_path,
        TOKEN,
        request,
    )
    requests, responses, cancelled = prepare_authorization_runtime(tmp_path)

    assert (requests / f"{TOKEN}.request").read_bytes() == request.serialize()
    (responses / f"{TOKEN}.response").write_bytes(b"source_available\n")
    assert read_authorization_response(tmp_path, TOKEN) == "source_available"
    remove_authorization_response(tmp_path, TOKEN)
    assert not (responses / f"{TOKEN}.response").exists()

    cancel_authorization(tmp_path, TOKEN)
    assert (cancelled / f"{TOKEN}.cancel").exists()


def test_api_queue_operations_do_not_reinitialize_host_owned_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requests, responses, cancelled = prepare_authorization_runtime(tmp_path)
    source_directory = tmp_path / "authorization-sources"
    monkeypatch.setattr(
        "app.workers.runner.provider_authorization_queue.os.chmod",
        lambda *_args, **_kwargs: pytest.fail(
            "API queue operations must not chmod host-owned directories"
        ),
    )

    write_authorization_request(
        tmp_path,
        TOKEN,
        ProviderAuthorizationRequest(
            ProviderKey.YOUTUBE,
            datetime.now(UTC) + timedelta(minutes=5),
        ),
    )
    cancel_authorization(tmp_path, TOKEN)

    assert S_IMODE((requests / f"{TOKEN}.request").stat().st_mode) == 0o644
    assert S_IMODE((cancelled / f"{TOKEN}.cancel").stat().st_mode) == 0o644
    assert S_IMODE(requests.stat().st_mode) == 0o733
    assert S_IMODE(responses.stat().st_mode) == 0o733
    assert S_IMODE(source_directory.stat().st_mode) == 0o700


def test_request_is_not_published_when_payload_fsync_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requests, _responses, _cancelled = prepare_authorization_runtime(tmp_path)
    monkeypatch.setattr(
        "app.workers.runner.provider_authorization_queue.os.fsync",
        lambda _descriptor: (_ for _ in ()).throw(OSError("simulated fsync failure")),
    )

    with pytest.raises(OSError, match="simulated fsync failure"):
        write_authorization_request(
            tmp_path,
            TOKEN,
            ProviderAuthorizationRequest(
                ProviderKey.YOUTUBE,
                datetime.now(UTC) + timedelta(minutes=5),
            ),
        )

    assert list(requests.iterdir()) == []


def test_invalid_authorization_tokens_are_ignored(tmp_path: Path) -> None:
    prepare_authorization_runtime(tmp_path)

    assert read_authorization_response(tmp_path, "not-a-token") is None
    cancel_authorization(tmp_path, "not-a-token")
    assert not list((tmp_path / "control" / "cancelled").iterdir())


def test_agent_authorizes_a_request_without_persisting_cookie_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_authorization_runtime(tmp_path)
    request = ProviderAuthorizationRequest(
        ProviderKey.REDDIT,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    write_authorization_request(tmp_path, TOKEN, request)
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        agent.subprocess,
        "run",
        lambda command, **_kwargs: actions.append(command),
    )
    leases = iter(
        (
            agent.ProviderCookieLease(  # type: ignore[attr-defined]
                agent.ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED
            ),
            agent.ProviderCookieLease(
                agent.ProviderCookieLeaseStatus.OK,
                b"private-cookie-payload",
            ),
        )
    )
    monkeypatch.setattr(
        agent,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: next(leases),
    )
    monkeypatch.setattr(agent.time, "sleep", lambda _seconds: None)

    agent.drain_authorization_requests(
        tmp_path,
        profile="Default",
        browser_root=tmp_path / "browser-root",
    )

    response = read_authorization_response(tmp_path, TOKEN)
    assert response == "source_available"
    assert read_authorization_source(tmp_path, ProviderKey.REDDIT) is (
        ProviderAuthorizationSource.DEDICATED_CHROME
    )
    assert not (tmp_path / "control" / "requests" / f"{TOKEN}.request").exists()
    assert actions[0][-1] == "https://www.reddit.com/"
    assert (
        b"private-cookie-payload"
        not in (tmp_path / "control" / "responses" / f"{TOKEN}.response").read_bytes()
    )


def test_agent_checks_current_chrome_without_opening_a_new_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_authorization_runtime(tmp_path)
    request = ProviderAuthorizationRequest(
        ProviderKey.YOUTUBE,
        datetime.now(UTC) + timedelta(minutes=5),
        ProviderAuthorizationSource.CURRENT_CHROME,
    )
    write_authorization_request(tmp_path, TOKEN, request)
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        agent.subprocess,
        "run",
        lambda command, **_kwargs: actions.append(command),
    )
    ProviderBrowserBridgeStore(tmp_path).write(
        ProviderKey.YOUTUBE,
        b"# Netscape HTTP Cookie File\n"
        b".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tprivate-cookie-payload\n",
    )

    agent.drain_authorization_requests(
        tmp_path,
        profile="Default",
        browser_root=tmp_path / "browser-root",
    )

    assert actions == []
    assert read_authorization_source(tmp_path, ProviderKey.YOUTUBE) is (
        ProviderAuthorizationSource.CURRENT_CHROME
    )
    assert read_authorization_response(tmp_path, TOKEN) == "source_available"


def test_agent_finishes_immediately_when_macos_denies_current_chrome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_authorization_runtime(tmp_path)
    request = ProviderAuthorizationRequest(
        ProviderKey.YOUTUBE,
        datetime.now(UTC) + timedelta(minutes=5),
        ProviderAuthorizationSource.CURRENT_CHROME,
    )
    write_authorization_request(tmp_path, TOKEN, request)
    monkeypatch.setattr(
        agent,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: agent.ProviderCookieLease(  # type: ignore[attr-defined]
            agent.ProviderCookieLeaseStatus.PERMISSION_DENIED  # type: ignore[attr-defined]
        ),
    )
    monkeypatch.setattr(
        agent.time,
        "sleep",
        lambda _seconds: pytest.fail("permission denial must not poll for ten minutes"),
    )
    monkeypatch.setattr(agent, "BROWSER_BRIDGE_HANDSHAKE_SECONDS", 0)

    agent.drain_authorization_requests(
        tmp_path,
        profile="Default",
        browser_root=tmp_path / "browser-root",
    )

    assert (
        read_authorization_response(tmp_path, TOKEN)
        == "provider_session_permission_denied"
    )
