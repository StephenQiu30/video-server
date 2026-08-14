from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedDocumentImport,
)
from app.domain.documents import normalize_screenplay
from app.domain.imports import ImportErrorCode


class TextLimits(Protocol):
    @property
    def max_characters(self) -> int: ...

    @property
    def max_line_characters(self) -> int: ...


def normalized_document(
    source_path: Path,
    claim: ImportVerificationClaim,
    *,
    original_sha256: str,
    original_size_bytes: int,
    extracted_text: str,
    limits: TextLimits,
) -> VerifiedDocumentImport:
    _validate_text(extracted_text, limits)
    try:
        screenplay = normalize_screenplay(extracted_text)
    except ValueError as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, str(exc)
        ) from exc
    if (
        len(screenplay.text) > limits.max_characters
        or len(screenplay.text) > 2 * len(extracted_text) + 1
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
            "document normalization exceeded its budget",
        )
    encoded = screenplay.text.encode("utf-8")
    normalized_path = source_path.parent / "screenplay.md"
    normalized_path.write_bytes(encoded)
    return VerifiedDocumentImport(
        original_sha256=original_sha256,
        original_size_bytes=original_size_bytes,
        original_content_type=claim.source_format.content_type,
        normalized_path=normalized_path,
        normalized_sha256=hashlib.sha256(encoded).hexdigest(),
        normalized_size_bytes=len(encoded),
        detected_language=screenplay.detected_language,
        character_count=screenplay.character_count,
        scenes=screenplay.scenes,
        quality_warnings=screenplay.quality_warnings,
    )


def _validate_text(text: str, limits: TextLimits) -> None:
    if any(ord(character) < 32 and character not in "\t\n\r" for character in text):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
            "document contains forbidden control characters",
        )
    if any(127 <= ord(character) <= 159 for character in text):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
            "document contains forbidden control characters",
        )
    if len(text) > limits.max_characters or any(
        len(line) > limits.max_line_characters for line in text.splitlines()
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, "document text limit exceeded"
        )
