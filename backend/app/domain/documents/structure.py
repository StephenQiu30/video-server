from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_ENGLISH_HEADING = re.compile(
    r"^(?:INT|EXT|EST|INT/EXT|EXT/INT|I/E)\.?(?:\s|[-.:—])",
    re.IGNORECASE,
)
_CHINESE_HEADING = re.compile(
    r"^(?:内景|外景|内外景|外内景|内/外|外/内)(?:\s|[.。·、\-—:：]|$)"
)
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+")
_CHINESE_SPEAKER = re.compile(
    r"^[\u3400-\u9fff·・]{1,12}(?:[（(][^）)]{1,16}[）)])?\^?$"
)
_TRANSITION = re.compile(
    r"^(?:CUT TO:|DISSOLVE TO:|SMASH CUT TO:|FADE (?:IN|OUT)[.:]?|"
    r"切至[:：]?|转场[:：]?)$",
    re.IGNORECASE,
)


class ScreenplayElementKind(StrEnum):
    HEADING = "heading"
    ACTION = "action"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"


@dataclass(frozen=True, slots=True)
class ScreenplayElement:
    kind: ScreenplayElementKind
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Line:
    start: int
    end: int
    text: str

    @property
    def stripped(self) -> str:
        return self.text.strip()


def is_scene_heading(value: str) -> bool:
    candidate = scene_heading_text(value)
    return bool(_ENGLISH_HEADING.match(candidate) or _CHINESE_HEADING.match(candidate))


def scene_heading_text(value: str) -> str:
    return _MARKDOWN_HEADING.sub("", value.strip())


def parse_scene_elements(
    text: str, scene_start: int, scene_end: int
) -> tuple[ScreenplayElement, ...]:
    lines = _lines(text, scene_start, scene_end)
    elements: list[ScreenplayElement] = []
    in_dialogue = False
    for index, line in enumerate(lines):
        value = line.stripped
        if not value:
            in_dialogue = False
            continue
        inline = _tabbed_dialogue(line)
        if inline:
            elements.extend(inline)
            in_dialogue = True
            continue
        if is_scene_heading(value):
            kind = ScreenplayElementKind.HEADING
            in_dialogue = False
        elif _TRANSITION.match(value):
            kind = ScreenplayElementKind.ACTION
            in_dialogue = False
        elif in_dialogue and _is_parenthetical(value):
            kind = ScreenplayElementKind.PARENTHETICAL
        elif _is_speaker(value, _next_value(lines, index)):
            kind = ScreenplayElementKind.CHARACTER
            in_dialogue = True
        elif in_dialogue:
            kind = ScreenplayElementKind.DIALOGUE
        else:
            kind = ScreenplayElementKind.ACTION
        elements.append(ScreenplayElement(kind, line.start, line.end))
    return tuple(elements)


def _lines(text: str, start: int, end: int) -> tuple[_Line, ...]:
    lines: list[_Line] = []
    offset = start
    for raw in text[start:end].splitlines(keepends=True):
        body = raw.removesuffix("\n")
        leading = len(body) - len(body.lstrip())
        visible = body.rstrip()
        lines.append(_Line(offset + leading, offset + len(visible), body))
        offset += len(raw)
    return tuple(lines)


def _next_value(lines: tuple[_Line, ...], index: int) -> str:
    if index + 1 >= len(lines):
        return ""
    return lines[index + 1].stripped


def _is_speaker(value: str, following: str) -> bool:
    if not following or is_scene_heading(following):
        return False
    candidate = value.removeprefix("@").removesuffix("^").strip()
    if not candidate or len(candidate) > 64 or _TRANSITION.match(candidate):
        return False
    english_letters = [character for character in candidate if character.isalpha()]
    english = bool(english_letters) and all(
        not character.isascii() or not character.isalpha() or character.isupper()
        for character in candidate
    )
    return (
        value.startswith("@") or english or bool(_CHINESE_SPEAKER.fullmatch(candidate))
    )


def _is_parenthetical(value: str) -> bool:
    return (value.startswith("(") and value.endswith(")")) or (
        value.startswith("（") and value.endswith("）")
    )


def _tabbed_dialogue(line: _Line) -> tuple[ScreenplayElement, ...]:
    content = line.text.lstrip()
    if "\t" not in content:
        return ()
    speaker, dialogue = content.split("\t", 1)
    if not speaker.strip() or not dialogue.strip():
        return ()
    if not _is_speaker(speaker.strip(), dialogue.strip()):
        return ()
    speaker_start = line.start
    speaker_end = speaker_start + len(speaker.rstrip())
    dialogue_leading = len(dialogue) - len(dialogue.lstrip())
    dialogue_start = speaker_start + len(speaker) + 1 + dialogue_leading
    return (
        ScreenplayElement(ScreenplayElementKind.CHARACTER, speaker_start, speaker_end),
        ScreenplayElement(ScreenplayElementKind.DIALOGUE, dialogue_start, line.end),
    )
