#!/usr/bin/env python3
"""FrameFetch local control agent.

The agent exposes a token-protected HTTP control plane on the loopback interface.
It never reads or copies Codex/Claude credentials; provider CLIs remain responsible
for their own authentication stores.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

AGENT_VERSION = "0.1.0"
API_VERSION = "v1"
ENDPOINT_FILENAME = "endpoint.json"
LAUNCH_LOCK_FILENAME = "launch.lock"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 2.0
DEFAULT_START_TIMEOUT_SECONDS = 6.0

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def state_dir() -> Path:
    override = os.environ.get("FRAMEFETCH_AGENT_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "FrameFetch" / "agent"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "FrameFetch" / "agent"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "framefetch" / "agent"


def endpoint_path() -> Path:
    return state_dir() / ENDPOINT_FILENAME


def _secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)


def _atomic_write_private_json(path: Path, payload: dict[str, Any]) -> None:
    _secure_directory(path.parent)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary, path)
        if os.name != "nt":
            path.chmod(0o600)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def read_endpoint() -> dict[str, Any] | None:
    try:
        payload = json.loads(endpoint_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    required = {"baseUrl", "token", "pid", "version", "startedAt"}
    if not isinstance(payload, dict) or not required.issubset(payload):
        return None
    if not isinstance(payload["baseUrl"], str) or not payload["baseUrl"].startswith(
        "http://127.0.0.1:"
    ):
        return None
    if not isinstance(payload["token"], str) or len(payload["token"]) < 32:
        return None
    return payload


def _run_command(
    command: Sequence[str],
    *,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        list(command),
        capture_output=True,
        check=False,
        text=True,
        timeout=5,
    )


def _safe_version(executable: str, *, runner: CommandRunner) -> str | None:
    try:
        result = _run_command((executable, "--version"), runner=runner)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    first_line = (result.stdout or result.stderr).strip().splitlines()
    return first_line[0][:160] if first_line else None


def _probe_codex(executable: str, *, runner: CommandRunner) -> dict[str, Any]:
    try:
        result = _run_command((executable, "login", "status"), runner=runner)
    except subprocess.TimeoutExpired:
        return {"authenticated": False, "status": "timeout"}
    except OSError:
        return {"authenticated": False, "status": "unavailable"}
    authenticated = result.returncode == 0
    return {
        "authenticated": authenticated,
        "status": "ready" if authenticated else "login_required",
    }


def _probe_claude(executable: str, *, runner: CommandRunner) -> dict[str, Any]:
    try:
        result = _run_command((executable, "auth", "status", "--json"), runner=runner)
    except subprocess.TimeoutExpired:
        return {"authenticated": False, "status": "timeout"}
    except OSError:
        return {"authenticated": False, "status": "unavailable"}
    authenticated = False
    auth_method: str | None = None
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        authenticated = payload.get("loggedIn") is True
        raw_auth_method = payload.get("authMethod")
        if isinstance(raw_auth_method, str):
            auth_method = raw_auth_method[:64]
    response: dict[str, Any] = {
        "authenticated": authenticated,
        "status": "ready" if authenticated else "login_required",
    }
    if auth_method:
        response["authMethod"] = auth_method
    return response


def collect_diagnostics(
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    def inspect_provider(
        name: str,
        probe: Callable[..., dict[str, Any]],
    ) -> tuple[str, dict[str, Any]]:
        executable = which(name)
        if executable is None:
            return (
                name,
                {
                    "installed": False,
                    "authenticated": False,
                    "status": "not_installed",
                    "version": None,
                },
            )
        authentication = probe(executable, runner=runner)
        return (
            name,
            {
                "installed": True,
                "version": _safe_version(executable, runner=runner),
                **authentication,
            },
        )

    strategies = (("codex", _probe_codex), ("claude", _probe_claude))
    with ThreadPoolExecutor(max_workers=len(strategies)) as executor:
        results = executor.map(lambda item: inspect_provider(*item), strategies)
        providers = dict(results)
    return {"checkedAt": int(time.time()), "providers": providers}


def request_agent(
    method: str,
    route: str,
    *,
    endpoint: dict[str, Any] | None = None,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    selected = endpoint or read_endpoint()
    if selected is None:
        raise ConnectionError("FrameFetch Agent is not running")
    request = urllib.request.Request(
        f"{selected['baseUrl']}{route}",
        method=method,
        headers={
            "Authorization": f"Bearer {selected['token']}",
            "Content-Type": "application/json",
        },
        data=b"{}" if method != "GET" else None,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionError("FrameFetch Agent is not reachable") from error
    if not isinstance(payload, dict):
        raise ConnectionError("FrameFetch Agent returned an invalid response")
    return payload


def probe_agent(endpoint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        return request_agent("GET", "/v1/status", endpoint=endpoint, timeout=0.8)
    except ConnectionError:
        return None


def _remove_stale_endpoint() -> None:
    current = read_endpoint()
    if current is not None and probe_agent(current) is not None:
        return
    with contextlib.suppress(FileNotFoundError):
        endpoint_path().unlink()


def _spawn_agent(script_path: Path) -> None:
    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(script_path), "serve"], **kwargs)


def ensure_agent(
    script_path: Path | None = None,
    *,
    timeout: float = DEFAULT_START_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    current = probe_agent()
    if current is not None:
        return current
    _secure_directory(state_dir())
    lock_path = state_dir() / LAUNCH_LOCK_FILENAME
    deadline = time.monotonic() + timeout
    owns_lock = False
    try:
        while time.monotonic() < deadline:
            current = probe_agent()
            if current is not None:
                return current
            try:
                descriptor = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    if time.time() - lock_path.stat().st_mtime > timeout:
                        lock_path.unlink()
                except FileNotFoundError:
                    pass
                time.sleep(0.1)
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
            owns_lock = True
            _remove_stale_endpoint()
            _spawn_agent(script_path or Path(__file__).resolve())
            while time.monotonic() < deadline:
                current = probe_agent()
                if current is not None:
                    return current
                time.sleep(0.1)
            break
    finally:
        if owns_lock:
            with contextlib.suppress(FileNotFoundError):
                lock_path.unlink()
    raise TimeoutError("FrameFetch Agent did not become ready before the timeout")


class AgentState:
    def __init__(self, *, started_at: int) -> None:
        self.started_at = started_at
        self._lock = threading.Lock()
        self._diagnostics: dict[str, Any] = {
            "checkedAt": None,
            "providers": {
                "codex": {
                    "installed": None,
                    "authenticated": False,
                    "status": "checking",
                    "version": None,
                },
                "claude": {
                    "installed": None,
                    "authenticated": False,
                    "status": "checking",
                    "version": None,
                },
            },
        }

    def refresh(self) -> dict[str, Any]:
        diagnostics = collect_diagnostics()
        with self._lock:
            self._diagnostics = diagnostics
        return diagnostics

    def status(self) -> dict[str, Any]:
        with self._lock:
            diagnostics = dict(self._diagnostics)
        return {
            "agent": {
                "name": "framefetch-local-agent",
                "version": AGENT_VERSION,
                "apiVersion": API_VERSION,
                "pid": os.getpid(),
                "startedAt": self.started_at,
                "transport": "loopback_http",
            },
            **diagnostics,
        }


class AgentRequestHandler(BaseHTTPRequestHandler):
    server: AgentHttpServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = f"Bearer {self.server.token}"
        return secrets.compare_digest(self.headers.get("Authorization", ""), expected)

    def _require_authorization(self) -> bool:
        if self._authorized():
            return True
        self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def do_GET(self) -> None:
        if not self._require_authorization():
            return
        if self.path == "/v1/status":
            self._send_json(HTTPStatus.OK, self.server.agent_state.status())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if not self._require_authorization():
            return
        if self.path == "/v1/diagnostics":
            self.server.agent_state.refresh()
            self._send_json(HTTPStatus.OK, self.server.agent_state.status())
            return
        if self.path == "/v1/stop":
            self._send_json(HTTPStatus.OK, {"stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


class AgentHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, token: str, agent_state: AgentState) -> None:
        super().__init__(("127.0.0.1", 0), AgentRequestHandler)
        self.token = token
        self.agent_state = agent_state


def serve() -> None:
    existing = probe_agent()
    if existing is not None:
        return
    _remove_stale_endpoint()
    started_at = int(time.time())
    token = secrets.token_urlsafe(32)
    agent_state = AgentState(started_at=started_at)
    server = AgentHttpServer(token, agent_state)
    port = server.server_address[1]
    endpoint = {
        "schemaVersion": 1,
        "baseUrl": f"http://127.0.0.1:{port}",
        "token": token,
        "pid": os.getpid(),
        "version": AGENT_VERSION,
        "startedAt": started_at,
    }
    _atomic_write_private_json(endpoint_path(), endpoint)
    threading.Thread(target=agent_state.refresh, daemon=True).start()

    def stop_server(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, stop_server)
        if os.name != "nt":
            signal.signal(signal.SIGINT, stop_server)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        current = read_endpoint()
        if current is not None and current.get("pid") == os.getpid():
            with contextlib.suppress(FileNotFoundError):
                endpoint_path().unlink()


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="FrameFetch local control agent")
    parser.add_argument(
        "command",
        choices=("serve", "start", "status", "doctor", "stop"),
    )
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve()
            return 0
        if args.command == "start":
            _print_json(ensure_agent())
            return 0
        if args.command == "status":
            status = probe_agent()
            if status is None:
                _print_json({"running": False})
                return 1
            _print_json({"running": True, **status})
            return 0
        if args.command == "doctor":
            ensure_agent()
            _print_json(request_agent("POST", "/v1/diagnostics"))
            return 0
        endpoint = read_endpoint()
        if endpoint is None or probe_agent(endpoint) is None:
            _remove_stale_endpoint()
            _print_json({"stopped": True, "wasRunning": False})
            return 0
        _print_json(request_agent("POST", "/v1/stop", endpoint=endpoint))
        return 0
    except (ConnectionError, TimeoutError) as error:
        _print_json({"error": str(error)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
