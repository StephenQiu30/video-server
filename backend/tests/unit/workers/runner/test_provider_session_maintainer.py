from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from app.services.provider_types import ProviderKey
from app.workers.runner import provider_session_maintainer as maintainer
from app.workers.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.workers.runner.provider_session_setup import publish_session
from app.workers.runner.provider_sessions import credential_revision

COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-only\n"
)


def test_refresh_publishes_changed_youtube_source_and_private_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "youtube"
    state = tmp_path / "state"
    publish_session(ProviderKey.YOUTUBE, source, COOKIE)
    replacement = COOKIE.replace(b"fixture-only", b"replacement")
    revision_secret = b"unit-test-maintainer-hmac-secret"
    monkeypatch.setattr(
        maintainer,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.OK, replacement
        ),
    )

    result = maintainer.refresh_youtube_source(
        source,
        state_root=state,
        profile="Default",
        revision_secret=revision_secret,
    )

    assert result is maintainer.MaintenanceResult.UPDATED
    assert (source / "cookies.txt").read_bytes() == replacement
    document = json.loads((state / "state.json").read_text())
    assert document["status"] == "updated"
    assert document["provider"] == "youtube"
    assert document["revision"] == credential_revision(replacement, revision_secret)
    assert "cookie" not in json.dumps(document).casefold()
    assert stat.S_IMODE(state.stat().st_mode) == 0o700
    assert stat.S_IMODE((state / "state.json").stat().st_mode) == 0o600


def test_refresh_failure_preserves_previous_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "youtube"
    publish_session(ProviderKey.YOUTUBE, source, COOKIE)
    monkeypatch.setattr(
        maintainer,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.PERMISSION_DENIED
        ),
    )

    result = maintainer.refresh_youtube_source(
        source,
        state_root=tmp_path / "state",
        profile="Default",
        revision_secret=b"unit-test-maintainer-hmac-secret",
    )

    assert result is maintainer.MaintenanceResult.PERMISSION_DENIED
    assert (source / "cookies.txt").read_bytes() == COOKIE


def test_unchanged_refresh_does_not_publish_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "youtube"
    publish_session(ProviderKey.YOUTUBE, source, COOKIE)
    monkeypatch.setattr(
        maintainer,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
    )
    monkeypatch.setattr(
        maintainer,
        "publish_session",
        lambda *_args, **_kwargs: pytest.fail("unchanged source must not be rewritten"),
    )

    assert (
        maintainer.refresh_youtube_source(
            source,
            state_root=tmp_path / "state",
            profile="Default",
            revision_secret=b"unit-test-maintainer-hmac-secret",
        )
        is maintainer.MaintenanceResult.UNCHANGED
    )


def test_publish_failure_preserves_previous_source_and_records_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "youtube"
    state = tmp_path / "state"
    publish_session(ProviderKey.YOUTUBE, source, COOKIE)
    replacement = COOKIE.replace(b"fixture-only", b"replacement")
    monkeypatch.setattr(
        maintainer,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.OK, replacement
        ),
    )
    monkeypatch.setattr(
        maintainer,
        "publish_session",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    result = maintainer.refresh_youtube_source(
        source,
        state_root=state,
        profile="Default",
        revision_secret=b"unit-test-maintainer-hmac-secret",
    )

    assert result is maintainer.MaintenanceResult.SESSION_UNAVAILABLE
    assert (source / "cookies.txt").read_bytes() == COOKIE
    assert json.loads((state / "state.json").read_text())["status"] == (
        "provider_session_unavailable"
    )


def test_corrupt_previous_state_does_not_block_refresh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "youtube"
    state = tmp_path / "state"
    publish_session(ProviderKey.YOUTUBE, source, COOKIE)
    state.mkdir(mode=0o700)
    state_file = state / "state.json"
    state_file.write_text("not-json")
    state_file.chmod(0o600)
    monkeypatch.setattr(
        maintainer,
        "export_provider_cookie_lease_bounded",
        lambda **_kwargs: ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
    )

    result = maintainer.refresh_youtube_source(
        source,
        state_root=state,
        profile="Default",
        revision_secret=b"unit-test-maintainer-hmac-secret",
    )

    assert result is maintainer.MaintenanceResult.UNCHANGED
    assert json.loads(state_file.read_text())["status"] == "unchanged"


def test_start_refreshes_before_detaching_authorized_maintainer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    state = tmp_path / "state"
    source.mkdir(mode=0o700)
    captures: list[tuple[tuple[str, ...], dict[str, object]]] = []

    class Process:
        pid = 27182

        @staticmethod
        def poll() -> None:
            return None

        @staticmethod
        def terminate() -> None:
            pytest.fail("healthy maintainer must not be terminated")

    def spawn(command: tuple[str, ...], **kwargs: object) -> Process:
        captures.append((command, kwargs))
        return Process()

    monkeypatch.setattr(maintainer.sys, "platform", "darwin")
    monkeypatch.setattr(maintainer.sys, "executable", "/private/venv/bin/python")
    monkeypatch.setattr(maintainer, "_daemon_running", lambda _root: False)
    monkeypatch.setattr(
        maintainer,
        "refresh_youtube_source",
        lambda *_args, **_kwargs: maintainer.MaintenanceResult.UNCHANGED,
    )
    monkeypatch.setattr(maintainer, "_read_pid", lambda _root: 27182)
    monkeypatch.setattr(maintainer.subprocess, "Popen", spawn)

    maintainer.start_maintainer(
        source, state_root=state, profile="Profile 2", interval_seconds=90
    )

    assert captures[0][0] == (
        "/private/venv/bin/python",
        "-m",
        "app.workers.runner.provider_session_maintainer",
        "serve",
        "--directory",
        str(source),
        "--state-root",
        str(state),
        "--profile",
        "Profile 2",
        "--interval-seconds",
        "90",
    )
    assert captures[0][1]["start_new_session"] is True
    assert captures[0][1]["close_fds"] is True


def test_start_refuses_to_detach_when_initial_capture_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    monkeypatch.setattr(maintainer.sys, "platform", "darwin")
    monkeypatch.setattr(maintainer, "_daemon_running", lambda _root: False)
    monkeypatch.setattr(
        maintainer,
        "refresh_youtube_source",
        lambda *_args, **_kwargs: maintainer.MaintenanceResult.PERMISSION_DENIED,
    )
    monkeypatch.setattr(
        maintainer.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("failed capture must not start daemon"),
    )

    with pytest.raises(SystemExit, match="provider_session_permission_denied"):
        maintainer.start_maintainer(source, state_root=tmp_path / "state")


def test_status_reports_only_running_state_and_stable_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    maintainer._write_state(
        state,
        status=maintainer.MaintenanceResult.UNCHANGED,
        attempted_at="2026-09-15T00:00:00+00:00",
        succeeded_at="2026-09-15T00:00:00+00:00",
        revision="secret-revision-must-not-print",
    )
    monkeypatch.setattr(maintainer.sys, "platform", "darwin")
    monkeypatch.setattr(maintainer, "_daemon_running", lambda _root: True)

    assert maintainer.maintainer_status(state) == 0

    output = capsys.readouterr().out
    assert output == "running: unchanged\n"
    assert "revision" not in output
    assert "secret" not in output


def test_daemon_identity_requires_expected_command_and_state_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    maintainer._write_pid(state, 27182)
    monkeypatch.setattr(maintainer, "_process_exists", lambda _pid: True)
    monkeypatch.setattr(
        maintainer.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": (
                    "python -m app.workers.runner.provider_session_maintainer serve "
                    f"--state-root {state}"
                ),
            },
        )(),
    )

    assert maintainer._daemon_running(state) is True

    monkeypatch.setattr(
        maintainer.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "python unrelated.py"}
        )(),
    )
    assert maintainer._daemon_running(state) is False


def test_private_pid_file_is_bounded_to_current_user(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)

    maintainer._write_pid(state, 27182)

    assert maintainer._read_pid(state) == 27182
    assert stat.S_IMODE((state / "daemon.json").stat().st_mode) == 0o600
    assert json.loads((state / "daemon.json").read_text()) == {"pid": 27182}


def test_non_macos_start_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(maintainer.sys, "platform", "linux")

    with pytest.raises(SystemExit, match="requires macOS"):
        maintainer.start_maintainer(
            tmp_path / "source", state_root=tmp_path / "state", profile="Default"
        )
