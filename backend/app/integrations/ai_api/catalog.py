from __future__ import annotations

import asyncio
import time

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.integrations.ai_api.http import request_json
from app.integrations.ai_cli.errors import AnalysisCliError
from app.services.ai_model_catalog import AiModel, ModelCatalogUnavailable

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class _Architecture(BaseModel):
    input_modalities: tuple[str, ...] = ()
    output_modalities: tuple[str, ...] = ()


class _Model(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    context_length: int = Field(default=0, ge=0)
    architecture: _Architecture
    supported_parameters: tuple[str, ...] = ()


class _Catalog(BaseModel):
    data: list[_Model] = Field(max_length=10000)


class OpenRouterModelCatalog:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self._models: tuple[AiModel, ...] = ()
        self._expires = 0.0
        self._lock = asyncio.Lock()

    async def list_models(self) -> tuple[AiModel, ...]:
        async with self._lock:
            if time.monotonic() < self._expires:
                return self._models
            try:
                payload = await request_json(
                    "GET",
                    f"{OPENROUTER_BASE_URL}/models",
                    timeout_seconds=10,
                    maximum_bytes=8 * 1024**2,
                    transport=self._transport,
                )
                parsed = _Catalog.model_validate(payload)
            except (AnalysisCliError, ValidationError):
                raise ModelCatalogUnavailable() from None
            self._models = tuple(
                AiModel(
                    id=item.id,
                    name=item.name,
                    context_length=item.context_length,
                    input_modalities=item.architecture.input_modalities,
                    output_modalities=item.architecture.output_modalities,
                    supported_parameters=item.supported_parameters,
                )
                for item in parsed.data
            )
            self._expires = time.monotonic() + 300
            return self._models
