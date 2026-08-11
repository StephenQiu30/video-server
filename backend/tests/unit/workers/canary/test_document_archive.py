from __future__ import annotations

from pathlib import Path

import pytest
from app.workers.canary.document_archive import (
    ACCEPTED_MARKER,
    ACTIVE_INDEX_ROW,
    ARCHIVED_INDEX_ROW,
    DOCUMENTS,
    PENDING_MARKER,
    DocumentArchiveError,
    archive_017_documents,
    validate_017_documents,
)


def _repository(tmp_path: Path, marker: str) -> Path:
    docs = tmp_path / "docs"
    for folder, name in DOCUMENTS:
        path = docs / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# document\n\n{marker}\n", encoding="utf-8")
    (docs / "README.md").write_text(
        f"# index\n\n{ACTIVE_INDEX_ROW}\n", encoding="utf-8"
    )
    return tmp_path


def test_pending_acceptance_cannot_be_archived(tmp_path: Path) -> None:
    root = _repository(tmp_path, PENDING_MARKER)

    with pytest.raises(DocumentArchiveError, match="acceptance_not_accepted"):
        archive_017_documents(root)

    assert all((root / "docs" / folder / name).is_file() for folder, name in DOCUMENTS)
    assert not (root / "docs" / "archive").exists()


def test_accepted_documents_are_moved_and_indexed(tmp_path: Path) -> None:
    root = _repository(tmp_path, ACCEPTED_MARKER)

    ready_paths = validate_017_documents(root)
    result = archive_017_documents(root)

    assert len(ready_paths) == 4
    assert result.archived is True
    assert len(result.paths) == 4
    assert all(
        not (root / "docs" / folder / name).exists() for folder, name in DOCUMENTS
    )
    assert all(
        (root / "docs" / "archive" / "017" / name).is_file() for _, name in DOCUMENTS
    )
    index = (root / "docs" / "README.md").read_text(encoding="utf-8")
    assert ACTIVE_INDEX_ROW not in index
    assert ARCHIVED_INDEX_ROW in index


def test_archive_is_idempotent_after_success(tmp_path: Path) -> None:
    root = _repository(tmp_path, ACCEPTED_MARKER)
    first = archive_017_documents(root)

    second = archive_017_documents(root)

    assert first.archived is True
    assert second.archived is False
    assert second.paths == first.paths


def test_partial_archive_state_is_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path, ACCEPTED_MARKER)
    folder, name = DOCUMENTS[0]
    target = root / "docs" / "archive" / "017" / name
    target.parent.mkdir(parents=True)
    (root / "docs" / folder / name).rename(target)

    with pytest.raises(DocumentArchiveError, match="document_archive_state_invalid"):
        archive_017_documents(root)
