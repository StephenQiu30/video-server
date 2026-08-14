from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedDocumentImport,
)
from app.domain.imports import ContentKind, ImportErrorCode, ImportSourceFormat
from pypdf import PdfReader

from .normalization import normalized_document
from .pdf_policy import reject_active_pdf_content
from .source import verified_source
from .text import TextVerificationSettings


@dataclass(frozen=True, slots=True)
class PdfVerificationSettings:
    text: TextVerificationSettings
    max_pages: int = 300
    max_page_content_bytes: int = 8 * 1024**2
    max_total_content_bytes: int = 32 * 1024**2
    max_inspected_objects: int = 20_000
    min_text_characters: int = 40
    min_text_page_ratio: float = 0.8
    max_replacement_character_ratio: float = 0.01

    def __post_init__(self) -> None:
        if (
            min(
                self.max_pages,
                self.max_page_content_bytes,
                self.max_total_content_bytes,
                self.max_inspected_objects,
                self.min_text_characters,
            )
            <= 0
            or not 0 < self.min_text_page_ratio <= 1
            or not 0 <= self.max_replacement_character_ratio <= 1
        ):
            raise ValueError("PDF verification limits are invalid")


class PdfScreenplayVerifier:
    def __init__(self, workspace_root: Path, settings: PdfVerificationSettings) -> None:
        self._workspace_root = workspace_root.resolve()
        self._settings = settings

    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedDocumentImport:
        if (
            claim.content_kind is not ContentKind.SCREENPLAY
            or claim.source_format is not ImportSourceFormat.PDF
        ):
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_FORMAT_UNSUPPORTED,
                "unsupported PDF screenplay contract",
            )
        resolved, content, digest = verified_source(
            path,
            self._workspace_root,
            claim,
            max_size_bytes=self._settings.text.max_size_bytes,
            unsafe_code=ImportErrorCode.DOCUMENT_STRUCTURE_INVALID,
        )
        extracted_text = _extract_pdf_text(content, self._settings)
        return normalized_document(
            resolved,
            claim,
            original_sha256=digest,
            original_size_bytes=len(content),
            extracted_text=extracted_text,
            limits=self._settings.text,
        )


def _extract_pdf_text(content: bytes, settings: PdfVerificationSettings) -> str:
    if not content.startswith(b"%PDF-"):
        _reject_structure("PDF header is invalid")
    reader: PdfReader | None = None
    stream = BytesIO(content)
    try:
        reader = PdfReader(
            stream, strict=True, password=None, root_object_recovery_limit=0
        )
        if reader.is_encrypted:
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_ENCRYPTED,
                "encrypted PDF documents are forbidden",
            )
        reject_active_pdf_content(reader.root_object, settings.max_inspected_objects)
        page_count = len(reader.pages)
        if not 1 <= page_count <= settings.max_pages:
            _reject_structure("PDF page count exceeded its budget")
        return _extract_pages(reader, page_count, settings)
    except ImportVerificationRejected:
        raise
    except Exception as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_STRUCTURE_INVALID,
            "PDF could not be parsed safely",
        ) from exc
    finally:
        if reader is not None:
            with suppress(Exception):
                reader.close()


def _extract_pages(
    reader: PdfReader, page_count: int, settings: PdfVerificationSettings
) -> str:
    pages: list[str] = []
    total_content_bytes = 0
    visible_pages = 0
    visible_characters = 0
    extracted_characters = 0
    replacements = 0
    for page in reader.pages:
        contents = page.get_contents()
        content_size = 0 if contents is None else len(contents.get_data())
        total_content_bytes += content_size
        if (
            content_size > settings.max_page_content_bytes
            or total_content_bytes > settings.max_total_content_bytes
        ):
            _reject_structure("PDF content streams exceeded their budget")
        text = page.extract_text() or ""
        extracted_characters += len(text)
        if extracted_characters > settings.text.max_characters:
            _reject_text("PDF extracted text exceeded its budget")
        visible = sum(not character.isspace() for character in text)
        visible_characters += visible
        replacements += text.count("\ufffd")
        visible_pages += visible >= settings.min_text_characters
        pages.append(text)
    if (
        visible_characters < settings.min_text_characters
        or visible_pages / page_count < settings.min_text_page_ratio
        or replacements / max(visible_characters, 1)
        > settings.max_replacement_character_ratio
    ):
        _reject_text("PDF does not contain enough reliable extractable text")
    return "\n\n".join(pages)


def _reject_structure(message: str) -> None:
    raise ImportVerificationRejected(
        ImportErrorCode.DOCUMENT_STRUCTURE_INVALID, message
    )


def _reject_text(message: str) -> None:
    raise ImportVerificationRejected(ImportErrorCode.DOCUMENT_TEXT_UNAVAILABLE, message)
