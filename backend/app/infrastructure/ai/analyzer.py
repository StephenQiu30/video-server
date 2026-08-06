from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from pydantic import ValidationError

from app.domain.analysis import (
    AnalysisValidationError,
    Transcript,
    parse_analysis_result,
)
from app.infrastructure.ai.config import AnalysisModelConfig
from app.infrastructure.ai.error_mapping import provider_error
from app.infrastructure.ai.errors import ProviderInvalidResponse
from app.infrastructure.ai.models import (
    StructuredAnalysisModel,
    create_analysis_model,
)
from app.infrastructure.ai.prompts import analysis_messages
from app.infrastructure.ai.schemas import AnalysisPayload


class LangChainAnalyzer:
    def __init__(
        self,
        config: AnalysisModelConfig,
        *,
        model: StructuredAnalysisModel | None = None,
    ) -> None:
        self._config = config
        self._model = model or create_analysis_model(config)

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
                    expected_schema_version=self._config.schema_version,
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
            result = await self._model.ainvoke(
                analysis_messages(
                    transcript,
                    output_language=output_language,
                    schema_version=self._config.schema_version,
                    repair_summary=repair_summary,
                )
            )
            if isinstance(result, AnalysisPayload):
                return result
            return AnalysisPayload.model_validate(result)
        except (ValidationError, TypeError, ValueError) as error:
            raise ProviderInvalidResponse() from error
        except Exception as error:
            raise provider_error(error) from error
