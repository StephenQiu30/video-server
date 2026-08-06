from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.domain.analysis import (
    AnalysisValidationError,
    Transcript,
    parse_analysis_result,
)
from app.infrastructure.ai.config import OpenAIProviderConfig, create_openai_client
from app.infrastructure.ai.error_mapping import provider_error
from app.infrastructure.ai.errors import (
    ProviderInvalidResponse,
    ProviderRefused,
)
from app.infrastructure.ai.prompts import analysis_input
from app.infrastructure.ai.schemas import AnalysisPayload


class OpenAIAnalyzer:
    def __init__(
        self,
        config: OpenAIProviderConfig,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._config = config
        self._client = client or create_openai_client(config)

    async def analyze(
        self, transcript: Transcript, output_language: str
    ) -> Mapping[str, object]:
        repair_summary: str | None = None
        for attempt in range(2):
            try:
                payload = await self._request(
                    transcript,
                    output_language=output_language,
                    repair_summary=repair_summary,
                )
                mapping = cast(dict[str, object], payload.model_dump(mode="json"))
                parse_analysis_result(
                    mapping,
                    transcript,
                    expected_schema_version=self._config.analysis_schema_version,
                    expected_language=output_language,
                )
                return mapping
            except AnalysisValidationError as error:
                repair_summary = error.code.value
            except ProviderInvalidResponse:
                repair_summary = "invalid_structured_response"
            if attempt == 1:
                raise ProviderInvalidResponse()
        raise AssertionError("analysis repair loop exhausted")

    async def _request(
        self,
        transcript: Transcript,
        *,
        output_language: str,
        repair_summary: str | None,
    ) -> AnalysisPayload:
        try:
            response = await self._client.responses.parse(
                model=self._config.analysis_model,
                input=analysis_input(
                    transcript,
                    output_language=output_language,
                    schema_version=self._config.analysis_schema_version,
                    repair_summary=repair_summary,
                ),
                text_format=AnalysisPayload,
                timeout=self._config.analysis_timeout_seconds,
            )
        except (OpenAIError, TimeoutError, ValidationError) as error:
            raise provider_error(error) from error
        if _contains_refusal(response):
            raise ProviderRefused()
        parsed = getattr(response, "output_parsed", None)
        if not isinstance(parsed, AnalysisPayload):
            raise ProviderInvalidResponse()
        return parsed


def _contains_refusal(response: object) -> bool:
    output = getattr(response, "output", None)
    if not isinstance(output, Sequence) or isinstance(output, (str, bytes)):
        return False
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
            continue
        if any(getattr(part, "type", None) == "refusal" for part in content):
            return True
    return False
