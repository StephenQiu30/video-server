from __future__ import annotations

from pathlib import Path

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedDocumentImport,
)
from app.domain.imports import ImportErrorCode, ImportSourceFormat

from .docx import DocxScreenplayVerifier
from .pdf import PdfScreenplayVerifier
from .text import TextScreenplayVerifier

_TEXT_FORMATS = {
    ImportSourceFormat.TXT,
    ImportSourceFormat.MARKDOWN,
    ImportSourceFormat.FOUNTAIN,
}


class ScreenplayImportVerifier:
    def __init__(
        self,
        text: TextScreenplayVerifier,
        docx: DocxScreenplayVerifier,
        pdf: PdfScreenplayVerifier,
    ) -> None:
        self._text = text
        self._docx = docx
        self._pdf = pdf

    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedDocumentImport:
        if claim.source_format in _TEXT_FORMATS:
            return await self._text(path, claim)
        if claim.source_format is ImportSourceFormat.DOCX:
            return await self._docx(path, claim)
        if claim.source_format is ImportSourceFormat.PDF:
            return await self._pdf(path, claim)
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_FORMAT_UNSUPPORTED,
            "document format verifier is not available",
        )
