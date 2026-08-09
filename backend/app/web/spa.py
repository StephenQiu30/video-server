"""Static file delivery with safe SPA history fallback."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

RESERVED_PREFIXES = ("api", "health")


class SPAStaticFiles(StaticFiles):
    """Serve index.html for UI routes while preserving API 404 responses."""

    async def get_response(self, path: str, scope: MutableMapping[str, Any]) -> Any:
        normalized = path.lstrip("/")
        request_path = str(scope.get("path", path)).lstrip("/")
        first_segment = request_path.partition("/")[0]
        if first_segment in RESERVED_PREFIXES:
            raise HTTPException(status_code=404)
        try:
            response = await super().get_response(normalized, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        # Starlette redirects /history -> /history/ when dist/history/index.html
        # exists (Umi exportStatic emits real directories). Serve the directory
        # index directly so browser-route refreshes never bounce through a 307.
        if isinstance(response, RedirectResponse) and response.headers.get(
            "location", ""
        ).endswith("/"):
            return await super().get_response(
                f"{normalized}/index.html".lstrip("/"), scope
            )
        return response


def mount_frontend(app: FastAPI, directory: Path) -> bool:
    """Mount a built frontend when present and return whether it was mounted."""
    if not (directory / "index.html").is_file():
        return False
    app.mount("/", SPAStaticFiles(directory=directory, html=True), name="frontend")
    return True
