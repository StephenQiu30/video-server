from pathlib import Path

import app.runner.managed_chrome_cdp as managed_chrome_cdp
import pytest
from app.runner.managed_chrome_cdp import ChromeDevTools
from app.runner.managed_chrome_session import _chrome_arguments
from app.runner.managed_session_cookies import (
    SESSION_HEADER_COOKIE,
    decode_session_headers,
    session_cookie_jar,
)
from websockets.exceptions import ConnectionClosedError


def test_managed_chrome_session_minimizes_cookie_and_local_auth() -> None:
    jar = session_cookie_jar(
        [
            {
                "name": "analytics",
                "value": "yuanbao-only",
                "domain": ".yuanbao.tencent.com",
            },
            {
                "name": "unrelated",
                "value": "must-not-leak",
                "domain": ".example.com",
            },
        ],
        {
            "userId": "operator-id",
            "token": "operator-token",
            "headers": {
                "X-device-id": "device-id",
                "X-WebVersion": "2.83.1",
                "User-Agent": "Chrome/152",
                "Authorization": "must-not-pass",
            },
        },
    )

    values = {(cookie.domain, cookie.name): cookie.value for cookie in jar}
    assert values[(".yuanbao.tencent.com", "hy_user")] == "operator-id"
    assert values[(".yuanbao.tencent.com", "hy_token")] == "operator-token"
    assert values[(".yuanbao.tencent.com", "analytics")] == "yuanbao-only"
    assert all(value != "must-not-leak" for value in values.values())
    encoded = values[("session.yuanbao.tencent.com", SESSION_HEADER_COOKIE)]
    assert decode_session_headers(encoded) == {
        "X-device-id": "device-id",
        "X-WebVersion": "2.83.1",
        "User-Agent": "Chrome/152",
    }


def test_authorization_chrome_is_never_started_headless() -> None:
    arguments = _chrome_arguments(Path("/Applications/Chrome"), Path("/profile"))

    assert "--headless" not in " ".join(arguments)
    assert arguments[-1] == "https://yuanbao.tencent.com/"


def test_cdp_connection_close_is_a_recoverable_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def closed_connection(*_args: object, **_kwargs: object) -> object:
        raise ConnectionClosedError(None, None)

    monkeypatch.setattr(managed_chrome_cdp, "connect", closed_connection)

    with pytest.raises(OSError, match="managed Chrome is unavailable"):
        ChromeDevTools().command("ws://127.0.0.1/target", "Network.getAllCookies")


def test_cdp_reuses_the_single_managed_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    devtools = ChromeDevTools()
    requests: list[str] = []
    commands: list[tuple[str, str, dict[str, object] | None]] = []

    def response(request: object) -> object:
        requests.append(str(request))
        return [
            {
                "type": "page",
                "url": "https://ui.ptlogin2.qq.com/",
                "webSocketDebuggerUrl": "ws://127.0.0.1/page",
            }
        ]

    monkeypatch.setattr(devtools, "_json", response)
    monkeypatch.setattr(
        devtools,
        "command",
        lambda target, method, params=None: commands.append((target, method, params))
        or {},
    )

    first = devtools.page(9222, "https://yuanbao.tencent.com/")
    second = devtools.page(9222, "https://yuanbao.tencent.com/")

    assert first == second == "ws://127.0.0.1/page"
    assert len(requests) == 1
    assert commands == [
        (
            "ws://127.0.0.1/page",
            "Page.navigate",
            {"url": "https://yuanbao.tencent.com/"},
        )
    ]
