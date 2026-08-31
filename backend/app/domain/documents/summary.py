from __future__ import annotations

import re
from dataclasses import dataclass

from .screenplay import ScreenplayScene
from .structure import ScreenplayElementKind

_LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+\S")


@dataclass(frozen=True, slots=True)
class DocumentParseSummary:
    page_count: int | None
    paragraph_count: int
    heading_count: int
    list_item_count: int
    table_count: int
    dialogue_block_count: int

    def __post_init__(self) -> None:
        values = (
            self.paragraph_count,
            self.heading_count,
            self.list_item_count,
            self.table_count,
            self.dialogue_block_count,
        )
        if self.page_count is not None and self.page_count <= 0:
            raise ValueError("document page count must be positive")
        if self.paragraph_count <= 0 or any(value < 0 for value in values[1:]):
            raise ValueError("document parse summary counts are invalid")


def summarize_document(
    text: str,
    scenes: tuple[ScreenplayScene, ...],
    *,
    page_count: int | None = None,
    table_count: int = 0,
) -> DocumentParseSummary:
    non_empty_lines = tuple(line for line in text.splitlines() if line.strip())
    kinds = tuple(element.kind for scene in scenes for element in scene.elements)
    return DocumentParseSummary(
        page_count=page_count,
        paragraph_count=len(non_empty_lines),
        heading_count=sum(
            kind in {ScreenplayElementKind.HEADING, ScreenplayElementKind.SECTION}
            for kind in kinds
        ),
        list_item_count=sum(bool(_LIST_ITEM.match(line)) for line in non_empty_lines),
        table_count=table_count,
        dialogue_block_count=sum(
            kind is ScreenplayElementKind.DIALOGUE for kind in kinds
        ),
    )
