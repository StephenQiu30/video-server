"""Read Yuanbao authorization through a disposable Chrome profile."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

from app.runner.chrome_provider_cookies import extract_chrome_cookies
from app.runner.managed_chrome_cdp import ChromeDevTools
from app.runner.provider_session_headers import yuanbao_session_cookie_jar

_LOGIN_URL = "https://yuanbao.tencent.com/"
_CHROME_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)


class EphemeralYuanbaoSession:
    """Export only current Yuanbao auth state and destroy it after one export."""

    def __init__(self, profile: str) -> None:
        self._profile = profile
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._profile_root: Path | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._devtools = ChromeDevTools()

    def load(self) -> CookieJar:
        try:
            source_cookies = extract_chrome_cookies(
                ("yuanbao.tencent.com",),
                self._profile,
            )
            self._prepare_disposable_profile()
            port = self._start_browser()
            target = self._devtools.page(port, "about:blank")
            self._set_cookies(target, source_cookies)
            self._devtools.command(target, "Page.navigate", {"url": _LOGIN_URL})
            self._wait_for_page(target)
            cookies = self._devtools.command(target, "Network.getAllCookies").get(
                "cookies", []
            )
            return yuanbao_session_cookie_jar(cookies, self._evaluate_auth(target))
        finally:
            self.close()

    def close(self) -> None:
        profile_root = self._profile_root
        if profile_root is not None:
            endpoint = self._devtools.browser_endpoint(profile_root)
            if endpoint is not None:
                try:
                    self._devtools.command(endpoint, "Browser.close")
                except OSError:
                    pass
        process = self._process
        self._process = None
        self._devtools.reset_page()
        if process is not None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        temporary = self._temporary
        self._temporary = None
        self._profile_root = None
        if temporary is not None:
            temporary.cleanup()

    def _prepare_disposable_profile(self) -> None:
        """Create an empty profile so no unrelated origin data is copied."""
        temporary = tempfile.TemporaryDirectory(prefix="framefetch-yuanbao-")
        root = Path(temporary.name)
        os.chmod(root, 0o700)
        profile_root = root / "chrome-profile"
        profile_root.mkdir(mode=0o700)
        os.chmod(profile_root, 0o700)
        self._temporary = temporary
        self._profile_root = profile_root

    def _start_browser(self) -> int:
        profile_root = self._profile_root
        if profile_root is None:
            raise OSError("disposable Yuanbao profile is unavailable")
        executable = _chrome_executable()
        self._process = subprocess.Popen(
            _chrome_arguments(executable, profile_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _attempt in range(100):
            if self._process.poll() is not None:
                raise OSError("disposable Chrome exited during session export")
            port = self._devtools.active_port(profile_root)
            if port is not None and self._devtools.endpoint_ready(port):
                return port
            time.sleep(0.1)
        raise OSError("disposable Chrome did not publish a debug endpoint")

    def _set_cookies(self, target: str, jar: CookieJar) -> None:
        cookies = [_cdp_cookie(cookie) for cookie in jar]
        if cookies:
            self._devtools.command(target, "Network.setCookies", {"cookies": cookies})

    def _wait_for_page(self, target: str) -> None:
        expression = (
            "document.readyState === 'complete' && "
            "location.origin === 'https://yuanbao.tencent.com'"
        )
        for _attempt in range(100):
            result = self._devtools.command(
                target,
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True},
            )
            if result.get("result", {}).get("value") is True:
                return
            time.sleep(0.1)
        raise OSError("Yuanbao did not finish loading")

    def _evaluate_auth(self, target: str) -> dict[str, object]:
        expression = """
        (async () => {
          const direct = {
            userId: localStorage.getItem('yb_user_id') || '',
            token: localStorage.getItem('yb_token') || ''
          };
          if (!direct.userId || !direct.token) {
            for (let index = 0; index < localStorage.length; index += 1) {
              const key = localStorage.key(index) || '';
              if (!key.startsWith('LOCAL_AUTH_INFO_KEY_')) continue;
              try {
                const value = JSON.parse(localStorage.getItem(key) || '{}');
                if (value.userId && value.token) Object.assign(direct, value);
              } catch (_) {}
            }
          }
          let headers = {};
          if (window.$webApi?.getYbCommonHeaders) {
            headers = await window.$webApi.getYbCommonHeaders();
          }
          if (window.$webApi?.setContextualRequestHeaders) {
            const request = {url: '/api/weixin/get_parse_result', headers};
            await window.$webApi.setContextualRequestHeaders(request);
            headers = request.headers;
          }
          headers['User-Agent'] = navigator.userAgent;
          return {...direct, headers};
        })()
        """
        result = self._devtools.command(
            target,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        value = result.get("result", {}).get("value", {})
        if not isinstance(value, dict):
            return {}
        return {
            key: raw
            for key in ("userId", "token", "headers")
            if isinstance((raw := value.get(key)), (str, dict)) and raw
        }


def _cdp_cookie(cookie: Cookie) -> dict[str, object]:
    value: dict[str, object] = {
        "name": cookie.name,
        "value": cookie.value or "",
        "domain": cookie.domain,
        "path": cookie.path,
        "secure": cookie.secure,
    }
    if cookie.expires is not None:
        value["expires"] = cookie.expires
    return value


def _chrome_arguments(executable: Path, profile_root: Path) -> tuple[str, ...]:
    return (
        str(executable),
        f"--user-data-dir={profile_root}",
        "--profile-directory=Default",
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=0",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--headless=new",
        "about:blank",
    )


def _chrome_executable() -> Path:
    for candidate in _CHROME_PATHS:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    discovered = shutil.which("google-chrome") or shutil.which("chromium")
    if discovered is None:
        raise OSError("Google Chrome is required for Yuanbao session export")
    return Path(discovered)
