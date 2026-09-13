from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

import pytest
from app.runner import yuanbao_session as yuanbao


class FakeDevTools:
    def __init__(self) -> None:
        self.closed = False

    def page(self, _port: int, url: str) -> str:
        assert url == "about:blank"
        return "ws://page"

    def command(
        self, _target: str, method: str, params: dict[str, object] | None = None
    ) -> dict[str, Any]:
        if method == "Network.getAllCookies":
            return {"cookies": []}
        if method == "Runtime.evaluate":
            expression = str((params or {}).get("expression", ""))
            value: object = (
                True
                if "document.readyState" in expression
                else {"userId": "user", "token": "token"}
            )
            return {"result": {"value": value}}
        if method == "Browser.close":
            self.closed = True
        return {}

    def browser_endpoint(self, _root: Path) -> str:
        return "ws://browser"

    def reset_page(self) -> None:
        pass


def test_missing_source_does_not_create_a_browser_or_profile(tmp_path: Path) -> None:
    root = tmp_path / "yuanbao"
    assert list(yuanbao.YuanbaoSession(root=root).load()) == []
    assert not root.exists()


def test_source_survives_export_and_uses_private_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "yuanbao"
    root.mkdir(mode=0o700)
    (root / "sentinel").write_text("existing session")
    monkeypatch.setattr(
        yuanbao.YuanbaoSession, "_start_browser", lambda _self, **_kwargs: 9222
    )
    session = yuanbao.YuanbaoSession(root=root)
    session._devtools = FakeDevTools()  # type: ignore[assignment]
    assert {cookie.name for cookie in session.load()} >= {"hy_user", "hy_token"}
    assert (root / "sentinel").read_text() == "existing session"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / ".framefetch.lock").stat().st_mode) == 0o600
    session._acquire_profile(create=False)
    session.close()


def test_busy_source_does_not_close_the_login_browser(tmp_path: Path) -> None:
    root = tmp_path / "yuanbao"
    owner = yuanbao.YuanbaoSession(root=root)
    owner._acquire_profile(create=True)
    contender = yuanbao.YuanbaoSession(root=root)
    devtools = FakeDevTools()
    contender._devtools = devtools  # type: ignore[assignment]
    try:
        with pytest.raises(OSError):
            contender.load()
        assert not devtools.closed
    finally:
        owner.close()


def test_source_rejects_symlink(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    root = tmp_path / "yuanbao"
    root.symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError):
        yuanbao.YuanbaoSession(root=root).load()


def test_lock_rejects_symlink(tmp_path: Path) -> None:
    root = tmp_path / "yuanbao"
    root.mkdir(mode=0o700)
    target = tmp_path / "untouched"
    target.write_text("untouched")
    (root / ".framefetch.lock").symlink_to(target)
    with pytest.raises(OSError):
        yuanbao.YuanbaoSession(root=root).load()
    assert target.read_text() == "untouched"


@pytest.mark.parametrize("headed", [True, False])
def test_launch_arguments_use_only_the_managed_profile(
    tmp_path: Path, headed: bool
) -> None:
    arguments = yuanbao._chrome_arguments(Path("/test/chrome"), tmp_path, headed=headed)
    assert f"--user-data-dir={tmp_path}" in arguments
    assert ("--headless=new" in arguments) is not headed
    assert "--remote-allow-origins=*" not in arguments
    assert arguments[-1] == "about:blank"


def test_browser_stays_in_export_process_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class Process:
        def poll(self) -> None:
            return None

    def launch(*_args: object, **kwargs: object) -> Process:
        captured.update(kwargs)
        return Process()

    monkeypatch.setattr(yuanbao.subprocess, "Popen", launch)
    monkeypatch.setattr(yuanbao, "_chrome_executable", lambda: Path("/test/chrome"))
    session = yuanbao.YuanbaoSession(root=tmp_path)
    session._profile_root = tmp_path
    monkeypatch.setattr(session._devtools, "active_port", lambda _path: 9222)
    monkeypatch.setattr(session._devtools, "endpoint_ready", lambda _port: True)
    assert session._start_browser() == 9222
    assert captured.get("start_new_session", False) is False


def test_login_creates_private_source_and_releases_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "yuanbao"
    session = yuanbao.YuanbaoSession(root=root)
    session._devtools = FakeDevTools()  # type: ignore[assignment]
    launches: list[bool] = []

    def start(*, headed: bool = False) -> int:
        launches.append(headed)
        return 9222

    monkeypatch.setattr(session, "_start_browser", start)
    assert session.login(timeout_seconds=1)
    assert launches == [True]
    assert root.is_dir()
    assert session._lock_fd is None


def test_browser_failure_preserves_source_and_releases_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session = yuanbao.YuanbaoSession(root=tmp_path / "yuanbao")
    session._acquire_profile(create=True)

    def fail() -> None:
        raise OSError("browser failed")

    monkeypatch.setattr(session, "_close_browser", fail)
    with pytest.raises(OSError):
        session.close()
    assert session._lock_fd is None
    assert session._root.exists()
    another = yuanbao.YuanbaoSession(root=session._root)
    another._acquire_profile(create=False)
    another.close()


def test_nonprivate_source_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "yuanbao"
    root.mkdir(mode=0o755)
    with pytest.raises(OSError):
        yuanbao.YuanbaoSession(root=root).load()


def test_auth_rejects_nonstring_login_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    session = yuanbao.YuanbaoSession()
    monkeypatch.setattr(
        session._devtools,
        "command",
        lambda *_args: {
            "result": {"value": {"userId": {"id": "user"}, "token": {"id": "token"}}}
        },
    )
    assert session._evaluate_auth("ws://page") == {}
