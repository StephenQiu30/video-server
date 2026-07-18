"""Public source-format normalization boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from video_server.source._format_candidates import build_candidates
from video_server.source._format_ordering import deduplicate_and_sort
from video_server.source._format_types import NormalizedFormat

__all__ = ["NormalizedFormat", "normalize_formats"]


def normalize_formats(
    raw_formats: Sequence[Mapping[str, Any]], locale: str
) -> list[NormalizedFormat]:
    """Normalize extractor formats according to the frozen Design 004 rules."""

    return deduplicate_and_sort(build_candidates(raw_formats, locale))
