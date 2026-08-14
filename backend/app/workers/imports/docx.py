from __future__ import annotations

import stat
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile, ZipInfo

from app.application.import_execution import (
    ImportVerificationClaim,
    ImportVerificationRejected,
    VerifiedDocumentImport,
)
from app.domain.imports import ContentKind, ImportErrorCode, ImportSourceFormat
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from .normalization import normalized_document
from .source import verified_source
from .text import TextVerificationSettings

_REQUIRED = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
_FORBIDDEN_PREFIXES = ("word/activex/", "word/embeddings/")


@dataclass(frozen=True, slots=True)
class DocxVerificationSettings:
    text: TextVerificationSettings
    max_entries: int = 512
    max_entry_bytes: int = 16 * 1024**2
    max_uncompressed_bytes: int = 64 * 1024**2
    max_compression_ratio: int = 100

    def __post_init__(self) -> None:
        if (
            min(
                self.max_entries,
                self.max_entry_bytes,
                self.max_uncompressed_bytes,
                self.max_compression_ratio,
            )
            <= 0
        ):
            raise ValueError("DOCX verification limits must be positive")


class DocxScreenplayVerifier:
    def __init__(
        self, workspace_root: Path, settings: DocxVerificationSettings
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._settings = settings

    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedDocumentImport:
        if (
            claim.content_kind is not ContentKind.SCREENPLAY
            or claim.source_format is not ImportSourceFormat.DOCX
        ):
            raise ImportVerificationRejected(
                ImportErrorCode.DOCUMENT_FORMAT_UNSUPPORTED,
                "unsupported DOCX screenplay contract",
            )
        resolved, content, digest = verified_source(
            path,
            self._workspace_root,
            claim,
            max_size_bytes=self._settings.text.max_size_bytes,
            unsafe_code=ImportErrorCode.DOCUMENT_ARCHIVE_UNSAFE,
        )
        _validate_package(content, self._settings)
        return normalized_document(
            resolved,
            claim,
            original_sha256=digest,
            original_size_bytes=len(content),
            extracted_text=_extract_text(content),
            limits=self._settings.text,
        )


def _validate_package(content: bytes, settings: DocxVerificationSettings) -> None:
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_ENCRYPTED,
            "encrypted Office compound documents are forbidden",
        )
    if not content.startswith(b"PK"):
        _reject("DOCX is not an OOXML ZIP package")
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if not 1 <= len(entries) <= settings.max_entries:
                _reject("DOCX entry count exceeded its budget")
            names = [_validated_name(entry) for entry in entries]
            if len({name.casefold() for name in names}) != len(
                entries
            ) or not _REQUIRED <= set(names):
                _reject("DOCX package entries are incomplete or duplicated")
            total = 0
            for entry in entries:
                total += _validate_entry(entry, settings)
                if total > settings.max_uncompressed_bytes:
                    _reject("DOCX uncompressed size exceeded its budget")
                lowered = entry.filename.casefold()
                if (
                    lowered.endswith("vbaproject.bin")
                    or lowered.endswith(".bin")
                    or lowered.startswith(_FORBIDDEN_PREFIXES)
                ):
                    _reject("DOCX active or embedded content is forbidden")
                if lowered.endswith((".xml", ".rels")):
                    _validate_xml(
                        archive.read(entry), relationships=lowered.endswith(".rels")
                    )
            content_types = archive.read("[Content_Types].xml").lower()
            if b"macroenabled" in content_types or b"vba" in content_types:
                _reject("DOCX macro content type is forbidden")
    except ImportVerificationRejected:
        raise
    except (BadZipFile, OSError, RuntimeError, ValueError, ET.ParseError) as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_ARCHIVE_UNSAFE, "DOCX package is invalid"
        ) from exc


def _validated_name(entry: ZipInfo) -> str:
    name = entry.filename
    path = PurePosixPath(name)
    mode = entry.external_attr >> 16
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or any(part in {"", ".", ".."} for part in path.parts)
        or (path.parts and ":" in path.parts[0])
        or (mode != 0 and stat.S_ISLNK(mode))
    ):
        _reject("DOCX contains an unsafe archive path")
    return path.as_posix()


def _validate_entry(entry: ZipInfo, settings: DocxVerificationSettings) -> int:
    if entry.flag_bits & 0x1:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_ENCRYPTED, "encrypted DOCX entries are forbidden"
        )
    if entry.is_dir():
        return 0
    if entry.file_size < 0 or entry.file_size > settings.max_entry_bytes:
        _reject("DOCX entry size exceeded its budget")
    if entry.file_size / max(entry.compress_size, 1) > settings.max_compression_ratio:
        _reject("DOCX compression ratio exceeded its budget")
    return entry.file_size


def _validate_xml(payload: bytes, *, relationships: bool) -> None:
    lowered = payload.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        _reject("DOCX XML entities are forbidden")
    root = ET.fromstring(payload)
    if not relationships:
        return
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "Relationship":
            continue
        target = element.attrib.get("Target", "")
        mode = element.attrib.get("TargetMode", "")
        parsed = urlsplit(target)
        if mode.casefold() == "external" or parsed.scheme or parsed.netloc:
            _reject("DOCX external relationships are forbidden")


def _extract_text(content: bytes) -> str:
    try:
        document = Document(BytesIO(content))
        lines: list[str] = []
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                lines.append(block.text)
            elif isinstance(block, Table):
                for row in block.rows:
                    lines.append("\t".join(cell.text for cell in row.cells))
        return "\n".join(lines)
    except Exception as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_ARCHIVE_UNSAFE,
            "DOCX body could not be read safely",
        ) from exc


def _reject(message: str) -> None:
    raise ImportVerificationRejected(ImportErrorCode.DOCUMENT_ARCHIVE_UNSAFE, message)
