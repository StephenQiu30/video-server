from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any, Protocol, cast

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import SecretStr

from app.infrastructure.ai_cli.errors import AnalysisCliError

from .config import DeepSeekAdapterConfig


class StructuredInvoker(Protocol):
    async def ainvoke(self, value: object) -> object: ...


class StructuredModel(Protocol):
    def with_structured_output(
        self,
        schema: dict[str, Any],
        *,
        method: str,
        include_raw: bool,
    ) -> StructuredInvoker: ...


def build_model(config: DeepSeekAdapterConfig, api_key: str) -> StructuredModel:
    model = ChatDeepSeek.model_validate(
        {
            "model": config.model,
            "api_key": SecretStr(api_key),
            "base_url": config.base_url,
            "timeout": config.timeout_seconds,
            "max_retries": 2,
        }
    )
    return cast(StructuredModel, model)


async def invoke_structured(
    model: StructuredModel,
    *,
    prompt: str,
    schema: dict[str, Any],
    content: list[dict[str, Any]] | None,
    timeout_seconds: float,
    maximum_result_bytes: int,
) -> dict[str, Any]:
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    message_content = content or [{"type": "text", "text": prompt}]
    message_content[0]["text"] = (
        f"{message_content[0]['text']}\nJSON Schema：\n{schema_json}\n"
    )
    try:
        runnable = model.with_structured_output(
            schema, method="json_mode", include_raw=False
        )
        async with asyncio.timeout(timeout_seconds):
            langchain_content = cast(list[str | dict[Any, Any]], message_content)
            value = await runnable.ainvoke(
                [HumanMessage(content=langchain_content)]
            )
    except AuthenticationError as exc:
        raise AnalysisCliError("analysis_cli_not_authenticated") from exc
    except RateLimitError as exc:
        raise AnalysisCliError("analysis_provider_rate_limited") from exc
    except (APITimeoutError, TimeoutError) as exc:
        raise AnalysisCliError("analysis_cli_timeout") from exc
    except APIStatusError as exc:
        raise _status_error(exc) from exc
    except APIConnectionError as exc:
        raise AnalysisCliError("analysis_cli_failed") from exc
    except OutputParserException as exc:
        raise AnalysisCliError("invalid_model_output") from exc
    except NotImplementedError as exc:
        raise AnalysisCliError("analysis_cli_unsupported") from exc
    if not isinstance(value, Mapping):
        raise AnalysisCliError("invalid_model_output")
    result = dict(value)
    if len(json.dumps(result, ensure_ascii=False).encode()) > maximum_result_bytes:
        raise AnalysisCliError("analysis_resource_limit")
    return result


def _status_error(error: APIStatusError) -> AnalysisCliError:
    detail = str(error).casefold()
    if error.status_code in {401, 403}:
        return AnalysisCliError("analysis_cli_not_authenticated")
    if error.status_code == 429:
        return AnalysisCliError("analysis_provider_rate_limited")
    if error.status_code == 402 or any(
        marker in detail for marker in ("quota", "balance", "credit")
    ):
        return AnalysisCliError("analysis_provider_usage_limited")
    return AnalysisCliError("analysis_cli_failed")
