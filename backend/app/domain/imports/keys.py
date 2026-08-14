from __future__ import annotations

from uuid import UUID

from app.domain.imports.enums import ContentKind


def quarantine_object_key(
    content_kind: ContentKind, resource_id: UUID, attempt: int
) -> str:
    if isinstance(attempt, bool) or attempt <= 0:
        raise ValueError("import attempt must be positive")
    return f"quarantine/{content_kind.value}/{resource_id}/{attempt}/source"
