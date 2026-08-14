from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from app.domain.analysis import ScreenplayRewriteGlossary

_SOURCE_LANGUAGES = {"zh-CN", "en-US", "mixed", "unknown"}
_TARGET_LANGUAGES = {"zh-CN", "en-US"}


@dataclass(frozen=True, slots=True)
class ScreenplayGlossaryRequest:
    screenplay: Path
    workspace: Path
    screenplay_text: str = field(repr=False)
    source_language: str
    target_language: str
    skill_id: str
    skill_instructions: str
    custom_prompt: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.screenplay_text
            or self.source_language not in _SOURCE_LANGUAGES
            or self.target_language not in _TARGET_LANGUAGES
        ):
            raise ValueError("screenplay glossary request is invalid")
        _validate_instructions(
            self.skill_id, self.skill_instructions, self.custom_prompt
        )


@dataclass(frozen=True, slots=True)
class ScreenplayRewriteChunkRequest:
    screenplay: Path
    workspace: Path
    source_text: str = field(repr=False)
    context_before: str = field(repr=False)
    context_after: str = field(repr=False)
    source_scene_id: str
    part_no: int
    source_sha256: str
    target_language: str
    glossary: ScreenplayRewriteGlossary
    skill_id: str
    skill_instructions: str
    custom_prompt: str | None = None

    def __post_init__(self) -> None:
        digest = hashlib.sha256(self.source_text.encode()).hexdigest()
        if (
            not self.source_text
            or not self.source_scene_id.startswith("scene-")
            or isinstance(self.part_no, bool)
            or not isinstance(self.part_no, int)
            or self.part_no <= 0
            or self.source_sha256 != digest
            or self.target_language not in _TARGET_LANGUAGES
            or self.glossary.target_language != self.target_language
            or any(len(value) > 2_000 for value in self.contexts)
        ):
            raise ValueError("screenplay rewrite chunk request is invalid")
        _validate_instructions(
            self.skill_id, self.skill_instructions, self.custom_prompt
        )

    @property
    def contexts(self) -> tuple[str, str]:
        return self.context_before, self.context_after


def _validate_instructions(
    skill_id: str, skill_instructions: str, custom_prompt: str | None
) -> None:
    if any(not value.strip() for value in (skill_id, skill_instructions)):
        raise ValueError("screenplay rewrite labels cannot be blank")
    if custom_prompt is not None and (
        not custom_prompt.strip() or len(custom_prompt) > 4_000
    ):
        raise ValueError("custom prompt must be non-blank and at most 4000 chars")
