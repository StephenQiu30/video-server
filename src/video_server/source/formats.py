"""Pure source-format normalization boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class NormalizedFormat(Protocol):
    """Public and test-oracle views of one normalized format candidate."""

    component_ids: tuple[str, ...]
    fingerprint_sha256: str

    def to_public_dict(self) -> dict[str, Any]: ...


def normalize_formats(
    raw_formats: Sequence[Mapping[str, Any]],
    locale: str,
) -> list[NormalizedFormat]:
    """Normalize extractor formats according to Design 004."""

    raise NotImplementedError("format normalization is not implemented")
