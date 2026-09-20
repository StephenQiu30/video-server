"""Own the explicitly authorized, local-only Yuanbao browser session."""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import stat
import subprocess
import time
from http.cookiejar import CookieJar
from pathlib import Path

from app.workers.runner._secure_file import no_follow_flag
from app.workers.runner.managed_chrome_cdp import ChromeDevTools
from app.workers.runner.provider_cookie_process import termination_guard
from app.workers.runner.provider_session_headers import yuanbao_session_cookie_jar

_LOGIN_URL = "https://yuanbao.tencent.com/"
DEFAULT_PROFILE_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "FrameFetch"
    / "provider-sessions"
    / "yuanbao"
)
_CHROME_PATHS = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)


class YuanbaoSession:
    """Persist one dedicated profile; export only a short-lived scoped lease."""

    def __init__(self, *, root: Path = DEFAULT_PROFILE_ROOT) -> None:
        self._root = root
        self._lock_fd: int | None = None
        self._profile_root: Path | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._devtools = ChromeDevTools()

    def load(self) -> CookieJar:
        try:
            if not self._root.exists() and not self._root.is_symlink():
                return CookieJar()
            self._acquire_profile(create=False)
            port = self._start_browser()
            target = self._devtools.page(port, "about:blank")
            self._devtools.command(target, "Page.navigate", {"url": _LOGIN_URL})
            self._wait_for_page(target)
            cookies = self._devtools.command(target, "Network.getAllCookies").get(
                "cookies", []
            )
            return yuanbao_session_cookie_jar(cookies, self._evaluate_auth(target))
        finally:
            self.close()

    def login(self, *, timeout_seconds: float = 600) -> bool:
        """Let the owner sign in interactively, then release the profile."""
        if not 0 < timeout_seconds <= 600:
            raise ValueError("login timeout must be between 0 and 600 seconds")
        try:
            self._acquire_profile(create=True)
            port = self._start_browser(headed=True)
            target = self._devtools.page(port, "about:blank")
            self._devtools.command(target, "Page.navigate", {"url": _LOGIN_URL})
            print(
                "请在帧取专用窗口登录腾讯元宝；检测到会话后会自动关闭窗口。", flush=True
            )
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                if self._process is not None and self._process.poll() is not None:
                    return False
                try:
                    auth = self._evaluate_auth(target)
                except OSError:
                    auth = {}
                if auth.get("userId") and auth.get("token"):
                    return True
                time.sleep(0.5)
            return False
        finally:
            self.close()

    def close(self) -> None:
        try:
            self._close_browser()
        finally:
            self._profile_root = None
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None

    def _close_browser(self) -> None:
        profile_root = self._profile_root
        if (
            profile_root is not None
            and self._process is not None
            and self._process.poll() is None
        ):
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

    def _acquire_profile(self, *, create: bool) -> None:
        root = self._root
        if not root.is_absolute() or any(
            path.is_symlink() for path in (root, *root.parents)
        ):
            raise OSError("unsafe Yuanbao profile path")
        if create:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = root.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise OSError("Yuanbao profile must be private to its owner")
        descriptor = os.open(
            root / ".framefetch.lock",
            os.O_CREAT | os.O_RDWR | no_follow_flag() | os.O_NONBLOCK,
            0o600,
        )
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != os.getuid()
                or opened.st_nlink != 1
                or opened.st_mode & 0o077
            ):
                raise OSError("unsafe Yuanbao session lock")
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(descriptor)
            raise
        self._lock_fd = descriptor
        self._profile_root = root

    def _start_browser(self, *, headed: bool = False) -> int:
        profile_root = self._profile_root
        if profile_root is None:
            raise OSError("Yuanbao profile is unavailable")
        # Never attach to a stale endpoint left by a previous browser.
        (profile_root / "DevToolsActivePort").unlink(missing_ok=True)
        executable = _chrome_executable()
        self._process = subprocess.Popen(
            _chrome_arguments(executable, profile_root, headed=headed),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # The export boundary owns the process group and must reap Chrome
            # too if page loading or graceful browser shutdown exceeds its limit.
            start_new_session=False,
        )
        for _attempt in range(100):
            if self._process.poll() is not None:
                raise OSError("managed Chrome exited during session export")
            port = self._devtools.active_port(profile_root)
            if port is not None and self._devtools.endpoint_ready(port):
                return port
            time.sleep(0.1)
        raise OSError("managed Chrome did not publish a debug endpoint")

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
          if (location.origin !== 'https://yuanbao.tencent.com') return {};
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
            for key, expected in (("userId", str), ("token", str), ("headers", dict))
            if isinstance((raw := value.get(key)), expected) and raw
        }


def _chrome_arguments(
    executable: Path, profile_root: Path, *, headed: bool = False
) -> tuple[str, ...]:
    return (
        str(executable),
        f"--user-data-dir={profile_root}",
        "--profile-directory=Default",
        "--remote-debugging-address=127.0.0.1",
        "--remote-debugging-port=0",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        *(("--new-window",) if headed else ("--headless=new",)),
        "--disable-sync",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="帧取专用元宝会话")
    parser.add_argument("command", choices=("login",))
    parser.parse_args()
    with termination_guard():
        try:
            saved = YuanbaoSession().login()
        except OSError:
            print("专用会话正在使用或浏览器不可用，请稍后重试。")
            return 1
    print(
        "会话已保存；仍需验证实际视频号下载。"
        if saved
        else "未确认登录；专用目录已保留，可重新运行登录。"
    )
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
