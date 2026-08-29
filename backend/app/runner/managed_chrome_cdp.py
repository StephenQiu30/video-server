"""Small CDP client for the isolated managed Chrome profile."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect


class ChromeDevTools:
    def __init__(self) -> None:
        self._page_target: str | None = None

    def reset_page(self) -> None:
        self._page_target = None

    def active_port(self, profile_root: Path) -> int | None:
        try:
            value = (profile_root / "DevToolsActivePort").read_text(
                encoding="utf-8"
            ).splitlines()[0]
            port = int(value)
        except (OSError, ValueError, IndexError):
            return None
        return port if 0 < port < 65536 else None

    def browser_endpoint(self, profile_root: Path) -> str | None:
        try:
            lines = (profile_root / "DevToolsActivePort").read_text(
                encoding="utf-8"
            ).splitlines()
            port = int(lines[0])
            route = lines[1]
        except (OSError, ValueError, IndexError):
            return None
        if not 0 < port < 65536 or not route.startswith("/devtools/browser/"):
            return None
        return f"ws://127.0.0.1:{port}{route}"

    def endpoint_ready(self, port: int) -> bool:
        try:
            return isinstance(self._json(f"http://127.0.0.1:{port}/json/version"), dict)
        except OSError:
            return False

    def page(self, port: int, url: str) -> str:
        if self._page_target is not None:
            return self._page_target
        targets = self._json(f"http://127.0.0.1:{port}/json/list")
        pages = (
            [
                target
                for target in targets
                if isinstance(target, dict)
                and target.get("type") == "page"
                and isinstance(target.get("webSocketDebuggerUrl"), str)
            ]
            if isinstance(targets, list)
            else []
        )
        preferred = next(
            (target for target in pages if str(target.get("url", "")).startswith(url)),
            pages[0] if pages else None,
        )
        if preferred is not None:
            target = str(preferred["webSocketDebuggerUrl"])
            if not str(preferred.get("url", "")).startswith(url):
                self.command(target, "Page.navigate", {"url": url})
            self._page_target = target
            return target
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/json/new?{url}", method="PUT"
        )
        created = self._json(request)
        if isinstance(created, dict) and isinstance(
            created.get("webSocketDebuggerUrl"), str
        ):
            self._page_target = str(created["webSocketDebuggerUrl"])
            return self._page_target
        raise OSError("managed Chrome did not expose its page")

    def command(
        self,
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
        except (OSError, TimeoutError, ValueError, WebSocketException) as exc:
            raise OSError("managed Chrome is unavailable") from exc

    @staticmethod
    def _json(request: str | urllib.request.Request) -> object:
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return json.load(response)
        except (OSError, ValueError) as exc:
            raise OSError("managed Chrome endpoint is unavailable") from exc
