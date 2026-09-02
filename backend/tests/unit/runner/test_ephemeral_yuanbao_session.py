from __future__ import annotations

from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

import pytest
from app.runner import ephemeral_yuanbao_session as yuanbao


class FakeDevTools:
    def page(self, _port: int, url: str) -> str:
        assert url == "about:blank"
        return "ws://page"

    def command(
        self,
        _target: str,
        method: str,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        if method == "Network.getAllCookies":
            return {"cookies": []}
        if method == "Runtime.evaluate":
            expression = str((params or {}).get("expression", ""))
            if "document.readyState" in expression:
                return {"result": {"value": True}}
            return {
                "result": {
                    "value": {
                        "userId": "user",
                        "token": "token",
                        "headers": {"x-platform": "web"},
                    }
                }
            }
        return {}

    def browser_endpoint(self, _profile_root: Path) -> None:
        return None

    def reset_page(self) -> None:
        pass


def test_yuanbao_uses_a_disposable_profile_and_removes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        yuanbao,
        "extract_chrome_cookies",
        lambda *_args, **_kwargs: CookieJar(),
    )
    monkeypatch.setattr(
        yuanbao.EphemeralYuanbaoSession,
        "_start_browser",
        lambda _self: 9222,
    )
    created: list[Path] = []
    original = yuanbao.EphemeralYuanbaoSession._prepare_disposable_profile

    def record_profile(
        session: yuanbao.EphemeralYuanbaoSession,
    ) -> None:
        original(session)
        assert session._profile_root is not None
        assert not (session._profile_root / "Default" / "Local Storage").exists()
        created.append(session._profile_root)

    monkeypatch.setattr(
        yuanbao.EphemeralYuanbaoSession,
        "_prepare_disposable_profile",
        record_profile,
    )
    session = yuanbao.EphemeralYuanbaoSession("Default")
    session._devtools = FakeDevTools()  # type: ignore[assignment]

    jar = session.load()

    assert {cookie.name for cookie in jar} >= {"hy_user", "hy_token"}
    assert len(created) == 1
    assert not created[0].exists()


def test_chrome_launch_uses_only_the_disposable_profile(tmp_path: Path) -> None:
    executable = Path("/Applications/Google Chrome")
    profile = tmp_path / "disposable"

    arguments = yuanbao._chrome_arguments(executable, profile)

    assert f"--user-data-dir={profile}" in arguments
    assert "--headless=new" in arguments
    assert arguments[-1] == "about:blank"
