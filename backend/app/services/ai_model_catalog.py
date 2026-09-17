"""Provider model metadata; capability declarations are not execution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AiModel:
    id: str
    name: str
    context_length: int
    input_modalities: tuple[str, ...]
    output_modalities: tuple[str, ...]
    supported_parameters: tuple[str, ...]

    def supports_analysis(self, *, images: bool) -> bool:
        required = {"text", "image"} if images else {"text"}
        return (
            required.issubset(self.input_modalities)
            and "text" in self.output_modalities
            and "structured_outputs" in self.supported_parameters
        )


class ModelCatalogUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ai_model_catalog_unavailable")


class AiModelCatalog(Protocol):
    async def list_models(self) -> tuple[AiModel, ...]: ...
