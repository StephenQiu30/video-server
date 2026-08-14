from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.text import identifier, required_text

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ScreenplayGlossaryTerm:
    source: str
    target: str
    category: str

    def __post_init__(self) -> None:
        for field_name in ("source", "target", "category"):
            object.__setattr__(
                self,
                field_name,
                required_text(getattr(self, field_name), f"glossary {field_name}"),
            )


@dataclass(frozen=True, slots=True)
class ScreenplayRewriteChunk:
    source_scene_id: str
    part_no: int
    source_sha256: str
    rewritten_text: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_scene_id",
            identifier(self.source_scene_id, "rewrite source scene id"),
        )
        if (
            isinstance(self.part_no, bool)
            or not isinstance(self.part_no, int)
            or self.part_no <= 0
        ):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "rewrite part_no must be a positive integer",
            )
        if not _SHA256.fullmatch(self.source_sha256):
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "rewrite source SHA-256 is invalid",
            )
        object.__setattr__(
            self,
            "rewritten_text",
            required_text(
                self.rewritten_text,
                "rewritten text",
                maximum=200_000,
            ),
        )
