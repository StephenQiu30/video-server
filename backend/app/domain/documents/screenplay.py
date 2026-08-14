from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

from .structure import (
    ScreenplayElement,
    is_scene_heading,
    parse_scene_elements,
    scene_heading_text,
)

_MAX_SCENES = 5_000
_MAX_ELEMENTS = 20_000


@dataclass(frozen=True, slots=True)
class ScreenplayScene:
    id: str
    start: int
    end: int
    elements: tuple[ScreenplayElement, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedScreenplay:
    text: str
    detected_language: str
    scenes: tuple[ScreenplayScene, ...]
    quality_warnings: tuple[str, ...]

    @property
    def character_count(self) -> int:
        return len(self.text)


def normalize_screenplay(text: str) -> NormalizedScreenplay:
    normalized = unicodedata.normalize("NFC", text.lstrip("\ufeff"))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.rstrip("\n") + "\n"
    if not normalized.strip():
        raise ValueError("screenplay text is empty")
    scenes = _scenes(normalized)
    warnings: tuple[str, ...] = ()
    if not scenes:
        digest = hashlib.sha256(normalized.encode()).hexdigest()[:12]
        elements = parse_scene_elements(normalized, 0, len(normalized))
        if len(elements) > _MAX_ELEMENTS:
            raise ValueError("screenplay structure element limit exceeded")
        scenes = (
            ScreenplayScene(
                f"scene-0001-{digest}",
                0,
                len(normalized),
                elements,
            ),
        )
        warnings = ("scene_heading_missing",)
    return NormalizedScreenplay(
        text=normalized,
        detected_language=_language(normalized),
        scenes=scenes,
        quality_warnings=warnings,
    )


def _scenes(text: str) -> tuple[ScreenplayScene, ...]:
    headings: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        candidate = scene_heading_text(line)
        if is_scene_heading(candidate):
            headings.append((offset, candidate))
            if len(headings) > _MAX_SCENES:
                raise ValueError("screenplay scene limit exceeded")
        offset += len(line)
    scenes: list[ScreenplayScene] = []
    element_count = 0
    for index, (start, heading) in enumerate(headings, start=1):
        end = headings[index][0] if index < len(headings) else len(text)
        identity = f"{index}:{heading.casefold()}".encode()
        digest = hashlib.sha256(identity).hexdigest()[:12]
        elements = parse_scene_elements(text, start, end)
        element_count += len(elements)
        if element_count > _MAX_ELEMENTS:
            raise ValueError("screenplay structure element limit exceeded")
        scenes.append(
            ScreenplayScene(
                f"scene-{index:04d}-{digest}",
                start,
                end,
                elements,
            )
        )
    return tuple(scenes)


def _language(text: str) -> str:
    chinese = sum("\u3400" <= character <= "\u9fff" for character in text)
    english = sum(character.isascii() and character.isalpha() for character in text)
    letters = chinese + english
    if letters < 20:
        return "unknown"
    if chinese / letters >= 0.2 and english / letters >= 0.2:
        return "mixed"
    return "zh-CN" if chinese > english else "en-US"
