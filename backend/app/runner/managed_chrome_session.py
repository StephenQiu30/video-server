"""Provider-scoped Chrome session owned by the local Session Broker."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

from websockets.sync.client import connect

from app.runner.managed_session_cookies import session_cookie_jar

_LOGIN_URL = "https://yuanbao.tencent.com/"
_CHROME_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)


class ManagedChromeCookieLoader:
    """Keep one isolated Chrome profile and expose its Yuanbao session."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root
        self._profile_root = state_root / "chrome-profile"
        self._process: subprocess.Popen[bytes] | None = None

    def __call__(self, browser: str, profile: str | None) -> CookieJar:
        if browser != "chrome" or profile is not None:
            raise ValueError("managed Yuanbao session requires its Chrome profile")
        port = self._ensure_browser()
        target = self._yuanbao_target(port)
        cookies = self._command(target, "Network.getAllCookies").get("cookies", [])
        auth = self._evaluate_auth(target)
        return session_cookie_jar(cookies, auth)

    def close(self) -> None:
        endpoint = _browser_websocket(self._profile_root / "DevToolsActivePort")
        if endpoint is not None:
            try:
                self._command(endpoint, "Browser.close")
            except OSError:
                pass
        if self._process is None:
            return
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)

    def _ensure_browser(self) -> int:
        self._secure_state_root()
        active_port = self._profile_root / "DevToolsActivePort"
        port = _active_port(active_port)
        if port is not None and _debug_endpoint_ready(port):
            return port
        executable = _chrome_executable()
        active_port.unlink(missing_ok=True)
        self._process = subprocess.Popen(
            (
                str(executable),
                f"--user-data-dir={self._profile_root}",
                "--remote-debugging-address=127.0.0.1",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-mode",
                _LOGIN_URL,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        for _attempt in range(100):
            if self._process.poll() is not None:
                raise OSError("managed Chrome exited during startup")
            port = _active_port(active_port)
            if port is not None and _debug_endpoint_ready(port):
                return port
            time.sleep(0.1)
        raise OSError("managed Chrome did not publish a debug endpoint")

    def _secure_state_root(self) -> None:
        self._state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._profile_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._state_root, 0o700)
        os.chmod(self._profile_root, 0o700)

    def _yuanbao_target(self, port: int) -> str:
        targets = _json_request(f"http://127.0.0.1:{port}/json/list")
        if isinstance(targets, list):
            for target in targets:
                if (
                    isinstance(target, dict)
                    and str(target.get("url", "")).startswith(_LOGIN_URL)
                    and isinstance(target.get("webSocketDebuggerUrl"), str)
                ):
                    return str(target["webSocketDebuggerUrl"])
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/json/new?{_LOGIN_URL}", method="PUT"
        )
        created = _json_request(request)
        if isinstance(created, dict) and isinstance(
            created.get("webSocketDebuggerUrl"), str
        ):
            return str(created["webSocketDebuggerUrl"])
        raise OSError("managed Chrome did not expose the Yuanbao page")

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
        result = self._command(
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

    @staticmethod
    def _command(
        target: str,
        method: str,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        request = {"id": 1, "method": method, "params": params or {}}
        try:
            with connect(target, open_timeout=3, close_timeout=1) as socket:
                socket.send(json.dumps(request, separators=(",", ":")))
                while True:
                    message = json.loads(socket.recv(timeout=5))
                    if message.get("id") != 1:
                        continue
                    if "error" in message:
                        raise OSError("managed Chrome command failed")
                    result = message.get("result", {})
                    return result if isinstance(result, dict) else {}
        except (OSError, TimeoutError, ValueError) as exc:
            raise OSError("managed Chrome is unavailable") from exc


def _active_port(path: Path) -> int | None:
    try:
        value = path.read_text(encoding="utf-8").splitlines()[0]
        port = int(value)
    except (OSError, ValueError, IndexError):
        return None
    return port if 0 < port < 65536 else None


def _browser_websocket(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        port = int(lines[0])
        route = lines[1]
    except (OSError, ValueError, IndexError):
        return None
    if not 0 < port < 65536 or not route.startswith("/devtools/browser/"):
        return None
    return f"ws://127.0.0.1:{port}{route}"


def _debug_endpoint_ready(port: int) -> bool:
    try:
        return isinstance(_json_request(f"http://127.0.0.1:{port}/json/version"), dict)
    except OSError:
        return False


def _json_request(request: str | urllib.request.Request) -> object:
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return json.load(response)
    except (OSError, ValueError) as exc:
        raise OSError("managed Chrome endpoint is unavailable") from exc


def _chrome_executable() -> Path:
    for candidate in _CHROME_PATHS:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    discovered = shutil.which("google-chrome") or shutil.which("chromium")
    if discovered is None:
        raise OSError("Google Chrome is required for the Yuanbao session")
    return Path(discovered)
