from __future__ import annotations

from uuid import UUID

_ARTIFACT_BASENAMES = {
    "mp4": "video",
    "webm": "video",
    "zip": "images",
}


def build_artifact_object_key(job_id: UUID, attempt: int, container: str) -> str:
    normalized = container.lower()
    basename = _ARTIFACT_BASENAMES.get(normalized)
    if attempt < 1 or basename is None:
        raise ValueError("invalid artifact attempt or container")
    return f"downloads/{job_id}/{attempt}/{basename}.{normalized}"
