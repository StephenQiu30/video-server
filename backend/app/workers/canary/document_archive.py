"""Move the accepted 017 document set into its historical archive."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ACCEPTED_MARKER = "<!-- acceptance: accepted -->"
PENDING_MARKER = "<!-- acceptance: pending -->"
ARCHIVE_NUMBER = "017"
DOCUMENTS = (
    ("design", "017-其他短视频平台分阶段接入设计.md"),
    ("prd", "017-其他短视频平台分阶段接入需求.md"),
    ("plans", "017-其他短视频平台分阶段接入计划.md"),
    ("acceptance", "017-其他短视频平台分阶段接入验收.md"),
)
ACTIVE_INDEX_ROW = (
    "| 017 | 其他短视频平台分阶段接入 | "
    "[Design](design/017-其他短视频平台分阶段接入设计.md) | "
    "[PRD](prd/017-其他短视频平台分阶段接入需求.md) | "
    "[Plan](plans/017-其他短视频平台分阶段接入计划.md) | "
    "[Acceptance](acceptance/017-其他短视频平台分阶段接入验收.md) |"
)
ARCHIVED_INDEX_ROW = (
    "| 017 | 其他短视频平台分阶段接入（已归档） | "
    "[Design](archive/017/017-其他短视频平台分阶段接入设计.md) | "
    "[PRD](archive/017/017-其他短视频平台分阶段接入需求.md) | "
    "[Plan](archive/017/017-其他短视频平台分阶段接入计划.md) | "
    "[Acceptance](archive/017/017-其他短视频平台分阶段接入验收.md) |"
)


class DocumentArchiveError(RuntimeError):
    """Report a stable reason instead of leaving a partial archive."""


@dataclass(frozen=True, slots=True)
class DocumentArchiveResult:
    archived: bool
    paths: tuple[str, ...]


def archive_017_documents(repo_root: Path) -> DocumentArchiveResult:
    _, sources, archive_root, targets, index = _document_paths(repo_root)
    validated_paths = validate_017_documents(repo_root)
    if all(path.is_file() for path in targets):
        return DocumentArchiveResult(False, validated_paths)
    index_text = index.read_text(encoding="utf-8")
    updated_index = index_text.replace(ACTIVE_INDEX_ROW, ARCHIVED_INDEX_ROW)

    archive_root.mkdir(parents=True, exist_ok=True)
    temporary_index = index.with_name(".README.md.archive.tmp")
    temporary_index.write_text(updated_index, encoding="utf-8", newline="")
    moved: list[tuple[Path, Path]] = []
    try:
        for source, target in zip(sources, targets, strict=True):
            source.rename(target)
            moved.append((source, target))
        os.replace(temporary_index, index)
    except Exception:
        temporary_index.unlink(missing_ok=True)
        for source, target in reversed(moved):
            target.rename(source)
        try:
            archive_root.rmdir()
            archive_root.parent.rmdir()
        except OSError:
            pass
        raise
    return DocumentArchiveResult(True, _relative_paths(repo_root, targets))


def validate_017_documents(repo_root: Path) -> tuple[str, ...]:
    _, sources, _, targets, index = _document_paths(repo_root)
    active_count = sum(path.is_file() for path in sources)
    archived_count = sum(path.is_file() for path in targets)
    if active_count == len(sources) and archived_count == 0:
        _validate_accepted(sources[-1])
        _validate_index(index, ACTIVE_INDEX_ROW)
        return _relative_paths(repo_root, sources)
    if active_count == 0 and archived_count == len(targets):
        _validate_accepted(targets[-1])
        _validate_index(index, ARCHIVED_INDEX_ROW)
        return _relative_paths(repo_root, targets)
    raise DocumentArchiveError("document_archive_state_invalid")


def _document_paths(
    repo_root: Path,
) -> tuple[Path, tuple[Path, ...], Path, tuple[Path, ...], Path]:
    docs_root = repo_root.resolve() / "docs"
    sources = tuple(docs_root / folder / name for folder, name in DOCUMENTS)
    archive_root = docs_root / "archive" / ARCHIVE_NUMBER
    targets = tuple(archive_root / name for _, name in DOCUMENTS)
    return docs_root, sources, archive_root, targets, docs_root / "README.md"


def _validate_accepted(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(ACCEPTED_MARKER) != 1 or PENDING_MARKER in text:
        raise DocumentArchiveError("acceptance_not_accepted")


def _validate_index(path: Path, expected_row: str) -> None:
    if path.read_text(encoding="utf-8").count(expected_row) != 1:
        raise DocumentArchiveError("document_index_invalid")


def _relative_paths(repo_root: Path, paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(path.relative_to(repo_root.resolve()).as_posix() for path in paths)
