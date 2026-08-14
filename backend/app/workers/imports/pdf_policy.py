from __future__ import annotations

from app.application.import_execution import ImportVerificationRejected
from app.domain.imports import ImportErrorCode
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    PdfObject,
    StreamObject,
)

_FORBIDDEN_KEYS = {
    "/AA",
    "/AF",
    "/EF",
    "/EmbeddedFiles",
    "/JS",
    "/JavaScript",
    "/OpenAction",
    "/RichMediaContent",
    "/RichMediaSettings",
    "/URI",
    "/XFA",
}
_FORBIDDEN_ACTIONS = {
    "/GoToE",
    "/GoToR",
    "/ImportData",
    "/JavaScript",
    "/Launch",
    "/Movie",
    "/Rendition",
    "/Sound",
    "/SubmitForm",
    "/URI",
}


def reject_active_pdf_content(root: DictionaryObject, max_objects: int) -> None:
    stack: list[PdfObject] = [root]
    indirect_seen: set[tuple[int, int]] = set()
    direct_seen: set[int] = set()
    inspected = 0
    try:
        while stack:
            current = stack.pop()
            if isinstance(current, IndirectObject):
                reference = (current.idnum, current.generation)
                if reference in indirect_seen:
                    continue
                indirect_seen.add(reference)
                resolved = current.get_object()
                if resolved is None:
                    continue
                current = resolved
            if not isinstance(current, (DictionaryObject, ArrayObject)):
                continue
            identity = id(current)
            if identity in direct_seen:
                continue
            direct_seen.add(identity)
            inspected += 1
            if inspected > max_objects:
                _reject("PDF object graph exceeded its inspection budget")
            if isinstance(current, ArrayObject):
                stack.extend(current)
                continue
            for key, value in current.items():
                name = str(key)
                if name in _FORBIDDEN_KEYS:
                    _reject("PDF active, external, or embedded content is forbidden")
                if isinstance(current, StreamObject) and name in {
                    "/F",
                    "/FDecodeParms",
                    "/FFilter",
                }:
                    _reject("PDF external stream resources are forbidden")
                if name == "/Type" and _object_name(value) == "/Filespec":
                    _reject("PDF file specifications are forbidden")
                if name == "/S" and _object_name(value) in _FORBIDDEN_ACTIONS:
                    _reject("PDF external or executable actions are forbidden")
                stack.append(value)
    except ImportVerificationRejected:
        raise
    except Exception as exc:
        raise ImportVerificationRejected(
            ImportErrorCode.DOCUMENT_STRUCTURE_INVALID,
            "PDF object graph could not be inspected safely",
        ) from exc


def _object_name(value: PdfObject) -> str:
    if isinstance(value, IndirectObject):
        resolved = value.get_object()
        return "" if resolved is None else str(resolved)
    return str(value)


def _reject(message: str) -> None:
    raise ImportVerificationRejected(
        ImportErrorCode.DOCUMENT_STRUCTURE_INVALID, message
    )
