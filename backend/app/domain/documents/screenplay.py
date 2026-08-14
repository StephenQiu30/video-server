from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

_ENGLISH_HEADING = re.compile(
    r"^(?:INT|EXT|EST|INT/EXT|EXT/INT|I/E)\.?(?:\s|[-.:—])",
    re.IGNORECASE,
)
_CHINESE_HEADING = re.compile(
    r"^(?:内景|外景|内外景|外内景|内/外|外/内)(?:\s|[.。·、\-—:：]|$)"
)
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+")


@dataclass(frozen=True, slots=True)
class ScreenplayScene:
    id: str
    start: int
    end: int


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
        scenes = (ScreenplayScene(f"scene-0001-{digest}", 0, len(normalized)),)
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
        candidate = _MARKDOWN_HEADING.sub("", line.strip())
        if _ENGLISH_HEADING.match(candidate) or _CHINESE_HEADING.match(candidate):
            headings.append((offset, candidate))
        offset += len(line)
    scenes: list[ScreenplayScene] = []
    for index, (start, heading) in enumerate(headings, start=1):
        end = headings[index][0] if index < len(headings) else len(text)
        identity = f"{index}:{heading.casefold()}".encode()
        digest = hashlib.sha256(identity).hexdigest()[:12]
        scenes.append(ScreenplayScene(f"scene-{index:04d}-{digest}", start, end))
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
