from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest
from app.runner import youtube_cookie_boundary as boundary
from app.runner.youtube_cookie_process import TerminationRequested, termination_guard


def _python(source: str, *args: str) -> tuple[str, ...]:
    return (sys.executable, "-c", source, *args)


@pytest.mark.parametrize(
    "status",
    ("ok", "credential_required", "provider_session_unavailable"),
)
def test_parent_accepts_only_exact_stable_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: str
) -> None:
    monkeypatch.setattr(
        boundary,
        "_child_command",
        lambda *args: _python("import sys; sys.stdout.write(sys.argv[1])", status),
    )

    assert boundary.sync_cookie_file_bounded(tmp_path) == status


@pytest.mark.parametrize(
    "source",
    (
        "print('unexpected')",
        "import sys; sys.stdout.buffer.write(b'\\xff')",
        "import sys; sys.exit(2)",
    ),
)
def test_parent_rejects_polluted_or_failed_child_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str
) -> None:
    monkeypatch.setattr(boundary, "_child_command", lambda *args: _python(source))

    assert boundary.sync_cookie_file_bounded(tmp_path) == "provider_session_unavailable"


def test_child_calls_sync_and_writes_only_the_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    staging = tmp_path / ".staging"
    calls: list[tuple[Path, str, str, Path]] = []

    def sync(
        secret: Path, *, profile: str, version: str, staging: Path
    ) -> boundary.SyncResult:
        calls.append((secret, profile, version, staging))
        return boundary.CREDENTIAL_REQUIRED

    monkeypatch.setattr(boundary, "sync_cookie_file", sync)

    result = boundary.main(
        (
            "child",
            "--secret-root",
            str(tmp_path),
            "--profile",
            "Default",
            "--version",
            "chrome-default",
            "--staging",
            str(staging),
        )
    )

    captured = capsys.readouterr()
    assert result == 0
    assert calls == [(tmp_path, "Default", "chrome-default", staging)]
    assert captured.out == "credential_required"
    assert captured.err == ""


def test_child_exception_is_a_stable_unavailable_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    staging = tmp_path / ".staging"

    def fail(*args: object, **kwargs: object) -> boundary.SyncResult:
        raise RuntimeError("internal detail")

    monkeypatch.setattr(boundary, "sync_cookie_file", fail)

    assert (
        boundary.main(
            (
                "child",
                "--secret-root",
                str(tmp_path),
                "--profile",
                "Default",
                "--version",
                "chrome-default",
                "--staging",
                str(staging),
            )
        )
        == 0
    )
    captured = capsys.readouterr()
    assert captured.out == "provider_session_unavailable"
    assert captured.err == ""


def test_child_unblocks_spawn_time_termination_signals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    staging = tmp_path / ".staging"
    observed: list[set[int | signal.Signals]] = []
    blocked = {signal.SIGTERM, signal.SIGINT, signal.SIGHUP}

    def sync(*args: object, **kwargs: object) -> boundary.SyncResult:
        observed.append(signal.pthread_sigmask(signal.SIG_BLOCK, set()))
        return boundary.OK

    monkeypatch.setattr(boundary, "sync_cookie_file", sync)
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        assert (
            boundary.main(
                (
                    "child",
                    "--secret-root",
                    str(tmp_path),
                    "--profile",
                    "Default",
                    "--version",
                    "chrome-default",
                    "--staging",
                    str(staging),
                )
            )
            == 0
        )
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)

    assert observed and not (observed[0] & blocked)
    assert capsys.readouterr().out == "ok"


def test_command_uses_current_python_and_module_cli(tmp_path: Path) -> None:
    staging = tmp_path / ".staging"
    command = boundary._child_command(tmp_path, "Default", "revision", staging)

    assert command[:4] == (
        sys.executable,
        "-m",
        "app.runner.youtube_cookie_boundary",
        "child",
    )
    assert command[-8:] == (
        "--secret-root",
        str(tmp_path),
        "--profile",
        "Default",
        "--version",
        "revision",
        "--staging",
        str(staging),
    )


def test_process_start_failure_is_a_stable_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("unavailable")

    monkeypatch.setattr(boundary.subprocess, "Popen", fail)

    assert boundary.sync_cookie_file_bounded(tmp_path) == "provider_session_unavailable"


def test_timeout_terminates_group_and_reaps_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent_pid = tmp_path / "parent.pid"
    child_pid = tmp_path / "child.pid"
    child_source = (
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(30)"
    )
    source = (
        "import os,pathlib,signal,subprocess,sys,time; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_source!r}]); "
        f"pathlib.Path({str(parent_pid)!r}).write_text(str(os.getpid())); "
        f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid)); "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    )
    monkeypatch.setattr(boundary, "_child_command", lambda *args: _python(source))

    result = boundary.sync_cookie_file_bounded(
        tmp_path,
        timeout_seconds=0.2,
        terminate_grace_seconds=0.05,
    )

    assert result == "provider_session_unavailable"
    _wait_until_missing(int(parent_pid.read_text()))
    _wait_until_missing(int(child_pid.read_text()))


def test_timeout_removes_the_exact_cookie_staging_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    staging_paths: list[Path] = []
    source = (
        "import pathlib,signal,sys,time; "
        "pathlib.Path(sys.argv[1]).write_bytes(b'synthetic-canary'); "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    )

    def command(*args: object) -> tuple[str, ...]:
        staging = args[-1]
        assert isinstance(staging, Path)
        staging_paths.append(staging)
        return _python(source, str(staging))

    monkeypatch.setattr(boundary, "_child_command", command)

    assert (
        boundary.sync_cookie_file_bounded(
            tmp_path,
            timeout_seconds=0.2,
            terminate_grace_seconds=0.05,
        )
        == "provider_session_unavailable"
    )
    assert len(staging_paths) == 1
    assert not staging_paths[0].exists()


def test_signal_in_spawn_window_is_delivered_after_child_registration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spawned: list[boundary.subprocess.Popen[bytes]] = []
    original = boundary.subprocess.Popen
    source = (
        "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "time.sleep(30)"
    )
    monkeypatch.setattr(boundary, "_child_command", lambda *args: _python(source))

    def spawn(*args: object, **kwargs: object) -> boundary.subprocess.Popen[bytes]:
        process = original(*args, **kwargs)  # type: ignore[arg-type]
        spawned.append(process)
        os.kill(os.getpid(), signal.SIGTERM)
        return process

    monkeypatch.setattr(boundary.subprocess, "Popen", spawn)

    with pytest.raises(TerminationRequested):
        boundary.sync_cookie_file_bounded(
            tmp_path,
            timeout_seconds=30,
            terminate_grace_seconds=0.05,
        )

    assert len(spawned) == 1
    _wait_until_missing(spawned[0].pid)


def test_signal_during_final_staging_unlink_is_delivered_after_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    staging_paths: list[Path] = []
    original_unlink = Path.unlink
    delivered = False
    monkeypatch.setattr(
        boundary,
        "_child_command",
        lambda *args: _python("import sys; sys.stdout.write('ok')"),
    )

    def create(secret_root: Path, version: str) -> Path:
        staging = secret_root / f".{version}.cookies.staging"
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.touch()
        staging_paths.append(staging)
        return staging

    def unlink(path: Path, *, missing_ok: bool = False) -> None:
        nonlocal delivered
        if staging_paths and path == staging_paths[0] and not delivered:
            delivered = True
            os.kill(os.getpid(), signal.SIGTERM)
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(boundary, "create_cookie_staging", create)
    monkeypatch.setattr(Path, "unlink", unlink)

    with termination_guard(), pytest.raises(TerminationRequested):
        boundary.sync_cookie_file_bounded(tmp_path)

    assert delivered is True
    assert staging_paths and not staging_paths[0].exists()


def _wait_until_missing(pid: int) -> None:
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    pytest.fail(f"process {pid} was not terminated")
