"""One-time isolated Chrome session used only for provider authorization."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from http.cookiejar import CookieJar
from pathlib import Path

from app.runner.managed_chrome_cdp import ChromeDevTools
from app.runner.managed_session_cookies import session_cookie_jar

_LOGIN_URL = "https://yuanbao.tencent.com/"
_CHROME_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)


class ManagedChromeCookieLoader:
    """Open one isolated login window and close it after authorization."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root
        self._profile_root = state_root / "chrome-profile"
        self._process: subprocess.Popen[bytes] | None = None
        self._devtools = ChromeDevTools()

    def __call__(self, browser: str, profile: str | None) -> CookieJar:
        if browser != "chrome" or profile is not None:
            raise ValueError("managed Yuanbao session requires its Chrome profile")
        for attempt in range(2):
            try:
                port = self._ensure_browser()
                target = self._devtools.page(port, _LOGIN_URL)
                cookies = self._devtools.command(
                    target, "Network.getAllCookies"
                ).get("cookies", [])
                return session_cookie_jar(cookies, self._evaluate_auth(target))
            except OSError:
                self._devtools.reset_page()
                if attempt == 1:
                    raise
        raise AssertionError("unreachable")

    def close(self) -> None:
        endpoint = self._devtools.browser_endpoint(self._profile_root)
        if endpoint is not None:
            try:
                self._devtools.command(endpoint, "Browser.close")
            except OSError:
                pass
        process = self._process
        self._process = None
        self._devtools.reset_page()
        if process is None:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def _ensure_browser(self) -> int:
        self._secure_state_root()
        port = self._devtools.active_port(self._profile_root)
        if port is not None and self._devtools.endpoint_ready(port):
            return port
        executable = _chrome_executable()
        (self._profile_root / "DevToolsActivePort").unlink(missing_ok=True)
        self._process = subprocess.Popen(
            _chrome_arguments(executable, self._profile_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _attempt in range(100):
            if self._process.poll() is not None:
                raise OSError("managed Chrome exited during authorization")
            port = self._devtools.active_port(self._profile_root)
            if port is not None and self._devtools.endpoint_ready(port):
                return port
            time.sleep(0.1)
        raise OSError("managed Chrome did not publish a debug endpoint")

    def _secure_state_root(self) -> None:
        self._state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._profile_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._state_root, 0o700)
        os.chmod(self._profile_root, 0o700)

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


def _chrome_arguments(executable: Path, profile_root: Path) -> tuple[str, ...]:
    return (
        str(executable),
        f"--user-data-dir={profile_root}",
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=0",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        _LOGIN_URL,
    )


def _chrome_executable() -> Path:
    for candidate in _CHROME_PATHS:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    discovered = shutil.which("google-chrome") or shutil.which("chromium")
    if discovered is None:
        raise OSError("Google Chrome is required for Yuanbao authorization")
    return Path(discovered)
