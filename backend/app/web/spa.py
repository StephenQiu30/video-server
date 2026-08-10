"""Static delivery for the exported Next.js frontend."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.staticfiles import StaticFiles

RESERVED_PREFIXES = ("api", "health")


class SPAStaticFiles(StaticFiles):
    """Serve Next.js route indexes while preserving API and UI 404 semantics."""

    async def get_response(self, path: str, scope: MutableMapping[str, Any]) -> Any:
        normalized = path.lstrip("/")
        request_path = str(scope.get("path", path)).lstrip("/")
        first_segment = request_path.partition("/")[0]
        if first_segment in RESERVED_PREFIXES:
            raise HTTPException(status_code=404)
        legacy_download_id = _legacy_download_id(normalized)
        if legacy_download_id is not None:
            return RedirectResponse(
                url=f"/downloads/detail?jobId={quote(legacy_download_id, safe='')}",
                status_code=308,
            )
        try:
            response = await super().get_response(normalized, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            not_found = await super().get_response("404.html", scope)
            not_found.status_code = 404
            return _with_frontend_cache_policy(not_found, "404.html")
        # Next.js exports route directories. Serve their index directly so a
        # refresh such as /downloads/detail?jobId=... never gains a 307 hop.
        if isinstance(response, RedirectResponse) and response.headers.get("location"):
            location = response.headers["location"]
            if not urlsplit(location).path.endswith("/"):
                return response
            route_response = await super().get_response(
                f"{normalized}/index.html".lstrip("/"), scope
            )
            return _with_frontend_cache_policy(route_response, request_path)
        return _with_frontend_cache_policy(response, request_path)


def _with_frontend_cache_policy(response: Response, path: str) -> Response:
    """Keep route HTML fresh while caching fingerprinted Next.js assets."""
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    elif path.startswith("_next/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


def _legacy_download_id(path: str) -> str | None:
    parts = path.rstrip("/").split("/")
    if len(parts) == 2 and parts[0] == "downloads" and parts[1] != "detail":
        return parts[1]
    return None


def mount_frontend(app: FastAPI, directory: Path) -> bool:
    """Mount a built frontend when present and return whether it was mounted."""
    if not (directory / "index.html").is_file():
        return False

    @app.get("/downloads/{download_id}", include_in_schema=False)
    async def legacy_download(download_id: str) -> Any:
        if download_id == "detail":
            detail = directory / "downloads" / "detail" / "index.html"
            if detail.is_file():
                return FileResponse(
                    detail,
                    headers={"Cache-Control": "no-store, max-age=0"},
                )
            raise HTTPException(status_code=404)
        return RedirectResponse(
            url=f"/downloads/detail?jobId={quote(download_id, safe='')}",
            status_code=308,
        )

    app.mount("/", SPAStaticFiles(directory=directory, html=True), name="frontend")
    return True
