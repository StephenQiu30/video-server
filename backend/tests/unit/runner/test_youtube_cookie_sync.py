from __future__ import annotations

import signal
import stat
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

import pytest
from app.runner import youtube_cookie_queue as queue
from app.runner import youtube_cookie_sync as sync
from app.runner.youtube_cookie_process import TerminationRequested


def _cookie(
    domain: str,
    *,
    name: str = "session",
    value: str = "secret-value",
    expires: int | None = 2_000_000_000,
    http_only: bool = False,
) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=expires,
        discard=expires is None,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": None} if http_only else {},
        rfc2109=False,
    )


def _jar(*cookies: Cookie) -> CookieJar:
    jar = CookieJar()
    for cookie in cookies:
        jar.set_cookie(cookie)
    return jar


def test_sync_exports_only_live_youtube_cookies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def extract(profile: str) -> CookieJar:
        captured["profile"] = profile
        return _jar(
            _cookie(".youtube.com", http_only=True),
            _cookie("www.youtube-nocookie.com", name="embed", value="allowed"),
            _cookie("accounts.google.com", name="google", value="excluded"),
            _cookie("youtube.com", name="expired", value="excluded", expires=1),
        )

    monkeypatch.setattr(sync, "extract_youtube_cookies", extract)

    result = sync.sync_cookie_file(
        tmp_path,
        profile="Default",
        version="chrome-default-v1",
        clock=lambda: 1_000,
    )

    target = tmp_path / "chrome-default-v1.cookies.txt"
    payload = target.read_text()
    assert result == "ok"
    assert captured["profile"] == "Default"
    assert "#HttpOnly_.youtube.com" in payload
    assert "youtube-nocookie.com" in payload
    assert "accounts.google.com" not in payload
    assert "expired" not in payload
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700


def test_sync_requires_an_eligible_cookie_without_replacing_previous_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "chrome-default-v1.cookies.txt"
    target.write_bytes(b"previous")
    monkeypatch.setattr(
        sync,
        "extract_youtube_cookies",
        lambda *args, **kwargs: _jar(_cookie("google.com")),
    )

    result = sync.sync_cookie_file(tmp_path, clock=lambda: 1_000)

    assert result == "credential_required"
    assert target.read_bytes() == b"previous"


def test_sync_refuses_a_symlink_secret_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "untrusted"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(
        sync,
        "extract_youtube_cookies",
        lambda *args, **kwargs: _jar(_cookie("youtube.com")),
    )

    assert sync.sync_cookie_file(linked) == "provider_session_unavailable"
    assert not tuple(target.iterdir())


def test_prepare_only_changes_owned_leaf_directories(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    shared.chmod(0o755)

    runtime = shared / "runtime"
    secret = shared / "secret"
    sync.prepare_runtime(runtime)
    sync.prepare_secret_root(secret)

    assert stat.S_IMODE(shared.stat().st_mode) == 0o755
    assert stat.S_IMODE(runtime.stat().st_mode) == 0o711
    assert stat.S_IMODE(secret.stat().st_mode) == 0o700


def test_sync_rejects_oversized_cookie_without_replacing_previous_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "chrome-default-v1.cookies.txt"
    target.write_bytes(b"previous")
    monkeypatch.setattr(
        sync,
        "extract_youtube_cookies",
        lambda *args, **kwargs: _jar(_cookie("youtube.com", value="x" * (1024**2))),
    )

    assert sync.sync_cookie_file(tmp_path) == "provider_session_unavailable"
    assert target.read_bytes() == b"previous"


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (FileNotFoundError(), "credential_required"),
        (RuntimeError("must never be returned"), "provider_session_unavailable"),
    ),
)
def test_sync_maps_browser_failures_to_stable_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: Exception,
    expected: str,
) -> None:
    def fail(*args: object, **kwargs: object) -> CookieJar:
        raise error

    monkeypatch.setattr(sync, "extract_youtube_cookies", fail)

    assert sync.sync_cookie_file(tmp_path) == expected


def test_drain_batches_requests_and_writes_exact_responses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    tokens = ("0" * 32, "a" * 32)
    for token in tokens:
        (requests / f"{token}.request").touch()
    (requests / f"{'A' * 32}.request").touch()
    calls: list[tuple[Path, str, str]] = []

    def refresh(secret_root: Path, *, profile: str, version: str) -> sync.SyncResult:
        calls.append((secret_root, profile, version))
        return sync.OK

    monkeypatch.setattr(sync, "sync_cookie_file", refresh)
    secret_root = tmp_path / "secret"
    published: dict[str, tuple[bytes, int]] = {}
    original = sync._atomic_write_response

    def consume(target: Path, result: sync.SyncResult) -> None:
        original(target, result)
        published[target.name] = (
            target.read_bytes(),
            stat.S_IMODE(target.stat().st_mode),
        )
        target.unlink()
        (requests / target.name.replace(".response", ".request")).unlink()

    monkeypatch.setattr(sync, "_atomic_write_response", consume)

    sync.drain_requests(
        runtime,
        secret_root,
        profile="Default",
        version="chrome-default-v1",
    )

    assert calls == [(secret_root, "Default", "chrome-default-v1")]
    assert not tuple(requests.iterdir())
    for token in tokens:
        assert published[f"{token}.response"] == (b"ok", 0o644)
    assert not tuple(responses.iterdir())


def test_drain_publishes_response_before_removing_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, _ = sync.prepare_runtime(runtime)
    request = requests / f"{'f' * 32}.request"
    request.touch()
    monkeypatch.setattr(sync, "sync_cookie_file", lambda *args, **kwargs: sync.OK)

    def publish(target: Path, result: sync.SyncResult) -> None:
        assert request.exists()
        assert result == "ok"

    monkeypatch.setattr(sync, "_atomic_write_response", publish)

    sync.drain_requests(
        runtime,
        tmp_path / "secret",
        acknowledgement_timeout_seconds=0,
    )

    assert not request.exists()


def test_drain_uses_bounded_refresh_callback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    token = "b" * 32
    (requests / f"{token}.request").touch()
    calls = 0

    def refresh() -> sync.SyncResult:
        nonlocal calls
        calls += 1
        return sync.SESSION_UNAVAILABLE

    published: list[bytes] = []

    def consume(target: Path, result: sync.SyncResult) -> None:
        published.append(result.encode())
        target.touch()
        target.unlink()
        (requests / f"{token}.request").unlink()

    monkeypatch.setattr(sync, "_atomic_write_response", consume)

    sync.drain_requests(
        runtime,
        tmp_path / "secret",
        refresh=refresh,
    )

    assert calls == 1
    assert published == [b"provider_session_unavailable"]
    assert not tuple(responses.iterdir())


def test_drain_removes_nonempty_invalid_directories(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    invalid = requests / f"{'c' * 32}.request"
    invalid.mkdir()
    (invalid / "payload").write_bytes(b"not-a-request")

    sync.drain_requests(runtime, tmp_path / "secret")

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_drain_quarantines_an_unreadable_invalid_directory(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    invalid = requests / "invalid"
    invalid.mkdir()
    (invalid / "payload").write_bytes(b"not-a-request")
    invalid.chmod(0)

    sync.drain_requests(runtime, tmp_path / "secret")

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())
    discarded = tuple((runtime / ".discarded").iterdir())
    assert len(discarded) == 1
    discarded[0].chmod(0o700)


def test_response_failure_consumes_request_and_continues_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    tokens = ("1" * 32, "2" * 32)
    for token in tokens:
        (requests / f"{token}.request").touch()
    calls: list[str] = []

    def publish(target: Path, result: sync.SyncResult) -> None:
        calls.append(target.name)
        if len(calls) == 1:
            raise OSError("response target unavailable")
        target.write_bytes(result.encode())
        target.unlink()
        (requests / target.name.replace(".response", ".request")).unlink()

    monkeypatch.setattr(sync, "_atomic_write_response", publish)

    sync.drain_requests(runtime, tmp_path / "secret", refresh=lambda: sync.OK)

    assert calls == [f"{token}.response" for token in tokens]
    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_cancellation_during_response_publish_cleans_all_queue_objects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    token = "3" * 32
    (requests / f"{token}.request").touch()

    def interrupt_fsync(descriptor: int) -> None:
        del descriptor
        raise TerminationRequested(signal.SIGTERM)

    monkeypatch.setattr(sync.os, "fsync", interrupt_fsync)

    with pytest.raises(TerminationRequested):
        sync.drain_requests(runtime, tmp_path / "secret", refresh=lambda: sync.OK)

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_cancellation_during_refresh_consumes_the_entire_batch(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    for token in ("4" * 32, "5" * 32):
        (requests / f"{token}.request").touch()

    def cancel() -> sync.SyncResult:
        raise TerminationRequested(signal.SIGTERM)

    with pytest.raises(TerminationRequested):
        sync.drain_requests(runtime, tmp_path / "secret", refresh=cancel)

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_cancellation_during_ack_wait_cleans_published_pairs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    token = "6" * 32
    (requests / f"{token}.request").touch()

    def cancel(delay: float) -> None:
        del delay
        raise TerminationRequested(signal.SIGTERM)

    monkeypatch.setattr(queue.time, "sleep", cancel)

    with pytest.raises(TerminationRequested):
        sync.drain_requests(runtime, tmp_path / "secret", refresh=lambda: sync.OK)

    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_cancellation_during_ack_cleanup_retries_the_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests, responses = sync.prepare_runtime(runtime)
    token = "7" * 32
    (requests / f"{token}.request").touch()
    original = queue._remove_entry
    calls = 0

    def interrupt_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TerminationRequested(signal.SIGTERM)
        original(path)

    monkeypatch.setattr(queue, "_remove_entry", interrupt_once)

    with pytest.raises(TerminationRequested):
        sync.drain_requests(
            runtime,
            tmp_path / "secret",
            refresh=lambda: sync.OK,
            acknowledgement_timeout_seconds=0,
        )

    assert calls > 1
    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())
