"""Bounded JSON transport shared by public discovery and paid completions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from app.integrations.ai_cli.errors import AnalysisCliError


async def request_json(
    method: str,
    url: str,
    *,
    timeout_seconds: float,
    maximum_bytes: int,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpx.AsyncClient(
                timeout=timeout_seconds,
                follow_redirects=False,
                transport=transport,
            ) as client:
                async with client.stream(
                    method, url, headers=headers, json=body
                ) as response:
                    if response.status_code != 200:
                        raise status_error(response.status_code)
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > maximum_bytes:
                            raise AnalysisCliError("analysis_resource_limit")
        value = json.loads(raw)
    except (httpx.TimeoutException, TimeoutError):
        raise AnalysisCliError("analysis_cli_timeout") from None
    except httpx.HTTPError:
        raise AnalysisCliError("analysis_cli_failed") from None
    except (ValueError, UnicodeError):
        raise AnalysisCliError("invalid_model_output") from None
    if not isinstance(value, dict):
        raise AnalysisCliError("invalid_model_output")
    error = value.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        raise status_error(code if isinstance(code, int) else 500)
    return value


def status_error(status: int) -> AnalysisCliError:
    code = {
        401: "analysis_cli_not_authenticated",
        403: "analysis_cli_not_authenticated",
        402: "analysis_provider_usage_limited",
        429: "analysis_provider_rate_limited",
        400: "analysis_cli_unsupported",
        404: "analysis_cli_unsupported",
        422: "analysis_cli_unsupported",
    }.get(status, "analysis_cli_failed")
    return AnalysisCliError(code)
