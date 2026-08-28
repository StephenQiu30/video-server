from __future__ import annotations

import json
import os
import stat
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

import app.runner.browser_cookie_export as browser_cookie_export
import pytest
from app.runner.browser_cookie_export import (
    export_browser_cookies,
)
from app.runner.provider_session_broker import run_session_broker


def _cookie(domain: str, name: str, value: str) -> Cookie:
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
        expires=2_147_483_647,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def _jar(*cookies: Cookie) -> CookieJar:
    jar = CookieJar()
    for cookie in cookies:
        jar.set_cookie(cookie)
    return jar


def test_export_filters_to_provider_domains_and_writes_read_only_secret(
    tmp_path: Path,
) -> None:
    source = _jar(
        _cookie(".youtube.com", "SID", "youtube-secret"),
        _cookie(".tiktok.com", "sessionid", "tiktok-secret"),
        _cookie(".example.com", "SID", "unrelated-secret"),
    )

    target, count = export_browser_cookies(
        provider="youtube",
        browser="chrome",
        profile=None,
        version="browser-v1",
        output_root=tmp_path / "secrets",
        cookie_loader=lambda _browser, _profile: source,
    )

    payload = target.read_text()
    assert count == 1
    assert "youtube-secret" in payload
    assert "tiktok-secret" not in payload
    assert "unrelated-secret" not in payload
    if os.name == "posix":
        assert stat.S_IMODE(target.stat().st_mode) == 0o400
        assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_export_requires_a_provider_login_cookie(tmp_path: Path) -> None:
    source = _jar(_cookie(".youtube.com", "PREF", "anonymous-cookie"))

    with pytest.raises(ValueError, match="login cookie was not found"):
        export_browser_cookies(
            provider="youtube",
            browser="chrome",
            profile=None,
            version="browser-v1",
            output_root=tmp_path / "secrets",
            cookie_loader=lambda _browser, _profile: source,
        )


@pytest.mark.parametrize(
    ("provider", "domain", "cookie_name"),
    (
        ("douyin", ".douyin.com", "ttwid"),
        ("xiaohongshu", ".xiaohongshu.com", "web_session"),
        ("reddit", ".reddit.com", "reddit_session"),
        ("x", ".x.com", "auth_token"),
        ("instagram", ".instagram.com", "sessionid"),
        ("facebook", ".facebook.com", "c_user"),
    ),
)
def test_export_supports_each_allowlisted_browser_session(
    tmp_path: Path,
    provider: str,
    domain: str,
    cookie_name: str,
) -> None:
    target, count = export_browser_cookies(
        provider=provider,
        browser="chrome",
        profile=None,
        version="browser-v1",
        output_root=tmp_path / "secrets",
        cookie_loader=lambda _browser, _profile: _jar(
            _cookie(domain, cookie_name, "provider-secret")
        ),
    )

    assert count == 1
    assert "provider-secret" in target.read_text()


def test_export_requires_complete_wechat_channels_yuanbao_session(
    tmp_path: Path,
) -> None:
    source = _jar(
        _cookie(".yuanbao.tencent.com", "hy_user", "operator-id"),
        _cookie(".yuanbao.tencent.com", "hy_token", "operator-token"),
        _cookie(".weixin.qq.com", "hy_token", "wrong-domain"),
    )

    target, count = export_browser_cookies(
        provider="wechat_channels",
        browser="chrome",
        profile=None,
        version="browser-v1",
        output_root=tmp_path / "secrets",
        cookie_loader=lambda _browser, _profile: source,
    )

    payload = target.read_text()
    assert count == 2
    assert "operator-id" in payload
    assert "operator-token" in payload
    assert "wrong-domain" not in payload

    with pytest.raises(ValueError, match="login cookie was not found"):
        export_browser_cookies(
            provider="wechat_channels",
            browser="chrome",
            profile=None,
            version="incomplete",
            output_root=tmp_path / "secrets",
            cookie_loader=lambda _browser, _profile: _jar(
                _cookie(".yuanbao.tencent.com", "hy_user", "operator-id")
            ),
        )


def test_export_auto_selects_the_browser_profile_with_provider_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anonymous_profile = tmp_path / "Default"
    authenticated_profile = tmp_path / "Profile 1"
    monkeypatch.setattr(
        browser_cookie_export,
        "_browser_profile_candidates",
        lambda _browser: (anonymous_profile, authenticated_profile),
    )

    def load(_browser: str, profile: str | None) -> CookieJar:
        if profile == str(authenticated_profile):
            return _jar(
                _cookie(".yuanbao.tencent.com", "hy_user", "operator-id"),
                _cookie(".yuanbao.tencent.com", "hy_token", "operator-token"),
            )
        return _jar(_cookie(".yuanbao.tencent.com", "analytics", "anonymous"))

    monkeypatch.setattr(browser_cookie_export, "_load_browser_cookies", load)

    target, count = export_browser_cookies(
        provider="wechat_channels",
        browser="chrome",
        profile=None,
        version="browser-v1",
        output_root=tmp_path / "secrets",
    )

    assert count == 2
    assert "operator-token" in target.read_text()


def test_export_rejects_symlinked_output_root(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "secrets"
    link.symlink_to(actual)

    with pytest.raises(ValueError, match="cannot be a symlink"):
        export_browser_cookies(
            provider="youtube",
            browser="chrome",
            profile=None,
            version="browser-v1",
            output_root=link,
            cookie_loader=lambda _browser, _profile: _jar(),
        )


def test_watch_refreshes_active_secret_when_browser_cookie_rotates(
    tmp_path: Path,
) -> None:
    sources = iter(
        (
            _jar(_cookie(".youtube.com", "SID", "session-one")),
            _jar(_cookie(".youtube.com", "SID", "session-two")),
        )
    )
    reports: list[str] = []

    status = tmp_path / "sessions" / "youtube.json"
    run_session_broker(
        provider="youtube",
        browser="chrome",
        profile=None,
        version="browser-live",
        output_root=tmp_path / "secrets",
        status_path=status,
        interval_seconds=5,
        cookie_loader=lambda _browser, _profile: next(sources),
        reporter=reports.append,
        sleeper=lambda _seconds: None,
        max_cycles=2,
    )

    payload = (
        tmp_path / "secrets" / "youtube" / "browser-live.cookies.txt"
    ).read_text()
    assert "session-two" in payload
    assert "session-one" not in payload
    assert reports == [
        "refreshed provider=youtube cookies=1 version=browser-live",
        "refreshed provider=youtube cookies=1 version=browser-live",
    ]
    assert json.loads(status.read_text())["state"] == "ready"


def test_watch_retains_last_good_secret_after_transient_browser_failure(
    tmp_path: Path,
) -> None:
    calls = 0

    def loader(_browser: str, _profile: str | None) -> CookieJar:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("browser temporarily unavailable")
        return _jar(_cookie(".youtube.com", "SID", "session-one"))

    reports: list[str] = []
    status = tmp_path / "sessions" / "youtube.json"
    run_session_broker(
        provider="youtube",
        browser="chrome",
        profile=None,
        version="browser-live",
        output_root=tmp_path / "secrets",
        status_path=status,
        interval_seconds=5,
        cookie_loader=loader,
        reporter=reports.append,
        sleeper=lambda _seconds: None,
        max_cycles=2,
    )

    payload = (
        tmp_path / "secrets" / "youtube" / "browser-live.cookies.txt"
    ).read_text()
    assert "session-one" in payload
    assert reports[-1] == "refresh_failed provider=youtube reason=ValueError"
    state = json.loads(status.read_text())
    assert state["provider"] == "youtube"
    assert state["state"] == "degraded"
    assert state["secret_ready"] is True
    assert state["updated_at"].endswith("+00:00")


def test_watch_waits_for_initial_wechat_login(tmp_path: Path) -> None:
    sources = iter(
        (
            _jar(_cookie(".yuanbao.tencent.com", "hy_user", "operator-id")),
            _jar(
                _cookie(".yuanbao.tencent.com", "hy_user", "operator-id"),
                _cookie(".yuanbao.tencent.com", "hy_token", "operator-token"),
            ),
        )
    )
    reports: list[str] = []

    status = tmp_path / "sessions" / "wechat_channels.json"
    run_session_broker(
        provider="wechat_channels",
        browser="chrome",
        profile=None,
        version="browser-live",
        output_root=tmp_path / "secrets",
        status_path=status,
        interval_seconds=5,
        cookie_loader=lambda _browser, _profile: next(sources),
        reporter=reports.append,
        sleeper=lambda _seconds: None,
        max_cycles=2,
    )

    payload = (
        tmp_path / "secrets" / "wechat_channels" / "browser-live.cookies.txt"
    ).read_text()
    assert "operator-id" in payload
    assert "operator-token" in payload
    assert reports == [
        "login_required provider=wechat_channels",
        "refreshed provider=wechat_channels cookies=2 version=browser-live",
    ]
    assert json.loads(status.read_text())["state"] == "ready"
