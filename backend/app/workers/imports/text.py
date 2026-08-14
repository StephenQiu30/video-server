from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass
from pathlib import Path

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedDocumentImport,
)
from app.domain.documents import normalize_screenplay
from app.domain.imports import ContentKind, ImportErrorCode, ImportSourceFormat

_READ_CHUNK = 1024 * 1024
_TEXT_FORMATS = {
    ImportSourceFormat.TXT,
    ImportSourceFormat.MARKDOWN,
    ImportSourceFormat.FOUNTAIN,
}


@dataclass(frozen=True, slots=True)
class TextVerificationSettings:
    max_size_bytes: int
    max_characters: int = 2_000_000
    max_line_characters: int = 20_000

    def __post_init__(self) -> None:
        if min(self.max_size_bytes, self.max_characters, self.max_line_characters) <= 0:
            raise ValueError("text verification limits must be positive")


class TextScreenplayVerifier:
    def __init__(
        self, workspace_root: Path, settings: TextVerificationSettings
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._settings = settings

    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedDocumentImport:
        if (
            claim.content_kind is not ContentKind.SCREENPLAY
            or claim.source_format not in _TEXT_FORMATS
        ):
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_FORMAT_UNSUPPORTED,
                "unsupported text screenplay contract",
            )
        resolved, content = _safe_content(
            path,
            self._workspace_root,
            declared_size=claim.declared_size_bytes,
            maximum_size=self._settings.max_size_bytes,
        )
        digest = hashlib.sha256(content).hexdigest()
        if digest != claim.declared_sha256:
            raise ImportVerificationRejected(
                ImportErrorCode.SHA256_MISMATCH, "document SHA-256 does not match"
            )
        try:
            decoded = content.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
                "document is not valid UTF-8",
            ) from exc
        _validate_text(decoded, self._settings)
        try:
            screenplay = normalize_screenplay(decoded)
        except ValueError as exc:
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, str(exc)
            ) from exc
        _validate_normalized(decoded, screenplay.text, self._settings)
        encoded = screenplay.text.encode("utf-8")
        normalized_path = resolved.parent / "screenplay.md"
        normalized_path.write_bytes(encoded)
        return VerifiedDocumentImport(
            original_sha256=digest,
            original_size_bytes=len(content),
            original_content_type=claim.source_format.content_type,
            normalized_path=normalized_path,
            normalized_sha256=hashlib.sha256(encoded).hexdigest(),
            normalized_size_bytes=len(encoded),
            detected_language=screenplay.detected_language,
            character_count=screenplay.character_count,
            scenes=screenplay.scenes,
            quality_warnings=screenplay.quality_warnings,
        )


def _safe_content(
    path: Path, root_path: Path, *, declared_size: int, maximum_size: int
) -> tuple[Path, bytes]:
    try:
        root_stat = root_path.lstat()
        parent_stat = path.parent.lstat()
        file_stat = path.lstat()
        root = root_path.resolve(strict=True)
        parent = path.parent.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
            "document workspace is unavailable",
        ) from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or stat.S_ISLNK(root_stat.st_mode)
        or not stat.S_ISDIR(parent_stat.st_mode)
        or stat.S_ISLNK(parent_stat.st_mode)
        or not stat.S_ISREG(file_stat.st_mode)
        or stat.S_ISLNK(file_stat.st_mode)
        or not parent.is_relative_to(root)
        or parent.parent != root
        or resolved.parent != parent
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, "unsafe document path"
        )
    if file_stat.st_size != declared_size or not 0 < file_stat.st_size <= maximum_size:
        raise ImportVerificationRejected(
            ImportErrorCode.SIZE_MISMATCH, "document size does not match"
        )
    return resolved, resolved.read_bytes()


def _validate_text(text: str, settings: TextVerificationSettings) -> None:
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
    if len(text) > settings.max_characters or any(
        len(line) > settings.max_line_characters for line in text.splitlines()
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, "document text limit exceeded"
        )


def _validate_normalized(
    source: str, normalized: str, settings: TextVerificationSettings
) -> None:
    if (
        len(normalized) > settings.max_characters
        or len(normalized) > 2 * len(source) + 1
    ):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE,
            "document normalization exceeded its budget",
        )
