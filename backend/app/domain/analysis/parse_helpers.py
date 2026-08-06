from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.result_models import AnalysisLimits


@dataclass(slots=True)
class ParseContext:
    limits: AnalysisLimits
    total_characters: int = 0
    node_count: int = 0
    seen_objects: set[int] = field(default_factory=set)

    def mapping(
        self,
        value: object,
        path: str,
        required: set[str],
        optional: set[str] | None = None,
    ) -> dict[str, object]:
        if not isinstance(value, dict) or any(
            not isinstance(key, str) for key in value
        ):
            self.invalid(f"{path} must be an object")
        mapping = cast(dict[str, object], value)
        allowed = required | (optional or set())
        if not required.issubset(mapping) or set(mapping) - allowed:
            self.invalid(f"{path} fields do not match the strict schema")
        return mapping

    def array(self, value: object, path: str, *, allow_empty: bool) -> list[object]:
        if not isinstance(value, list):
            self.invalid(f"{path} must be an array")
        array = cast(list[object], value)
        if (not allow_empty and not array) or len(
            array
        ) > self.limits.max_collection_items:
            code = (
                AnalysisValidationCode.INVALID_SCHEMA
                if not array
                else AnalysisValidationCode.LIMIT_EXCEEDED
            )
            raise AnalysisValidationError(code, f"{path} has an invalid item count")
        return array

    def text(self, value: object, path: str, *, maximum: int | None = None) -> str:
        limit = maximum or self.limits.max_string_characters
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.strip()) > limit
        ):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TEXT, f"{path} is invalid"
            )
        result = value.strip()
        self.total_characters += len(result)
        if self.total_characters > self.limits.max_total_characters:
            raise AnalysisValidationError(
                AnalysisValidationCode.LIMIT_EXCEEDED,
                "analysis result text exceeds the total limit",
            )
        return result

    def integer(self, value: object, path: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE, f"{path} is invalid"
            )
        return value

    def enter_node(self, value: dict[str, object], depth: int) -> None:
        identity = id(value)
        if identity in self.seen_objects:
            raise AnalysisValidationError(
                AnalysisValidationCode.DUPLICATE_IDENTIFIER,
                "mind map contains a repeated object or cycle",
            )
        self.seen_objects.add(identity)
        self.node_count += 1
        if (
            depth > self.limits.max_mind_map_depth
            or self.node_count > self.limits.max_mind_map_nodes
        ):
            raise AnalysisValidationError(
                AnalysisValidationCode.LIMIT_EXCEEDED,
                "mind map exceeds depth or node limits",
            )

    @staticmethod
    def invalid(detail: str) -> None:
        raise AnalysisValidationError(AnalysisValidationCode.INVALID_SCHEMA, detail)
