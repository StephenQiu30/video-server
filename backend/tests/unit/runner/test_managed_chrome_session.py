from app.runner.managed_session_cookies import (
    SESSION_HEADER_COOKIE,
    decode_session_headers,
    session_cookie_jar,
)


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
