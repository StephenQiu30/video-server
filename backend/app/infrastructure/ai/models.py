from __future__ import annotations

from typing import Any, Protocol, cast

from langchain_core.language_models.base import LanguageModelInput
from langchain_core.runnables import RunnableConfig
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
from pydantic import SecretStr

from app.infrastructure.ai.config import AnalysisModelConfig
from app.infrastructure.ai.schemas import AnalysisPayload


class StructuredAnalysisModel(Protocol):
    async def ainvoke(
        self,
        input: LanguageModelInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> object: ...


def create_analysis_model(config: AnalysisModelConfig) -> StructuredAnalysisModel:
    if config.provider == "deepseek":
        deepseek = ChatDeepSeek(
            model_name=config.model,
            api_key=SecretStr(config.api_key or ""),
            api_base=config.base_url,
            temperature=0,
            max_tokens=config.max_output_tokens,
            request_timeout=config.timeout_seconds,
            max_retries=0,
        )
        return cast(
            StructuredAnalysisModel,
            deepseek.with_structured_output(AnalysisPayload, method="json_mode"),
        )
    ollama = ChatOllama(
        model=config.model,
        base_url=config.base_url,
        temperature=0,
        reasoning=False,
        num_predict=config.max_output_tokens,
        client_kwargs={"timeout": config.timeout_seconds},
        async_client_kwargs={"timeout": config.timeout_seconds},
    )
    return cast(
        StructuredAnalysisModel,
        ollama.with_structured_output(AnalysisPayload, method="json_schema"),
    )
