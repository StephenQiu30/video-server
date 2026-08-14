from __future__ import annotations

from uuid import UUID

from app.domain.imports import ContentKind

CONTENT_IMPORT_VERIFY_REQUESTED = "content.import.verify.requested"


def import_verify_requested_payload(
    resource_id: UUID,
    content_kind: ContentKind,
    attempt: int,
    version: int,
) -> dict[str, str | int]:
    if isinstance(attempt, bool) or attempt <= 0:
        raise ValueError("import verification attempt must be positive")
    if isinstance(version, bool) or version < 0:
        raise ValueError("import resource version cannot be negative")
    return {
        "resource_id": str(resource_id),
        "content_kind": content_kind.value,
        "attempt": attempt,
        "version": version,
    }
