#!/usr/bin/env python3
"""Archive fully accepted document sets and keep references consistent."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROW_PATTERN = re.compile(
    r"^\| (?P<number>\d{3}) \| (?P<topic>[^|]+?) \| "
    r"\[Design\]\((?P<design>[^)]+)\) \| "
    r"\[PRD\]\((?P<prd>[^)]+)\) \| "
    r"\[Plan\]\((?P<plans>[^)]+)\) \| "
    r"\[Acceptance\]\((?P<acceptance>[^)]+)\) \|$",
    re.MULTILINE,
)
STATUS_PATTERN = re.compile(r"^- 状态：([^\r\n]+)$", re.MULTILINE)
REQUIRED_STATUSES = {
    "design": {"Accepted"},
    "prd": {"Accepted"},
    "plans": {"Complete", "Completed"},
    "acceptance": {"Accepted"},
}


class DocumentArchiveError(RuntimeError):
    """Reject an inconsistent document or archive state."""


@dataclass(frozen=True, slots=True)
class DocumentSet:
    number: str
    topic: str
    row: str
    links: tuple[tuple[str, str], ...]


def discover_ready_sets(repo_root: Path) -> tuple[DocumentSet, ...]:
    docs_root = repo_root.resolve() / "docs"
    index = (docs_root / "README.md").read_text(encoding="utf-8")
    ready: list[DocumentSet] = []
    for match in ROW_PATTERN.finditer(index):
        links = tuple((folder, match.group(folder)) for folder in REQUIRED_STATUSES)
        archived = [path.startswith("archive/") for _, path in links]
        if any(archived):
            if not all(archived):
                raise DocumentArchiveError(
                    f"document_archive_state_invalid:{match.group('number')}"
                )
            if not _has_required_statuses(docs_root, links):
                raise DocumentArchiveError(
                    f"document_archive_state_invalid:{match.group('number')}"
                )
            continue
        if _has_required_statuses(docs_root, links):
            ready.append(
                DocumentSet(
                    number=match.group("number"),
                    topic=match.group("topic").strip(),
                    row=match.group(0),
                    links=links,
                )
            )
    return tuple(ready)


def archive_completed_sets(repo_root: Path) -> tuple[str, ...]:
    root = repo_root.resolve()
    docs_root = root / "docs"
    ready = discover_ready_sets(root)
    if not ready:
        return ()
    moves: dict[Path, Path] = {}
    replacements: dict[str, str] = {}
    index_replacements: dict[str, str] = {}
    for document_set in ready:
        archived_links: list[tuple[str, str]] = []
        for folder, relative in document_set.links:
            source = docs_root / relative
            target = docs_root / "archive" / document_set.number / source.name
            if not source.is_file() or target.exists():
                raise DocumentArchiveError(
                    f"document_archive_state_invalid:{document_set.number}"
                )
            moves[source] = target
            replacements[f"docs/{relative}"] = (
                f"docs/archive/{document_set.number}/{source.name}"
            )
            archived_links.append(
                (folder, f"archive/{document_set.number}/{source.name}")
            )
        index_replacements[document_set.row] = _archived_row(
            document_set, tuple(archived_links)
        )

    updated_files: dict[Path, str] = {}
    markdown_files = (*docs_root.rglob("*.md"), *root.glob("*.md"))
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if markdown == docs_root / "README.md":
            for old, new in index_replacements.items():
                updated = updated.replace(old, new)
        if updated != text:
            updated_files[markdown] = updated

    for target in moves.values():
        target.parent.mkdir(parents=True, exist_ok=True)
    for source, target in moves.items():
        source.rename(target)
    for original, text in updated_files.items():
        destination = moves.get(original, original)
        destination.write_text(text, encoding="utf-8", newline="")
    return tuple(document_set.number for document_set in ready)


def _has_required_statuses(docs_root: Path, links: tuple[tuple[str, str], ...]) -> bool:
    for folder, relative in links:
        path = docs_root / relative
        if not path.is_file():
            return False
        match = STATUS_PATTERN.search(path.read_text(encoding="utf-8"))
        if match is None or match.group(1).strip() not in REQUIRED_STATUSES[folder]:
            return False
    return True


def _archived_row(document_set: DocumentSet, links: tuple[tuple[str, str], ...]) -> str:
    paths = dict(links)
    return (
        f"| {document_set.number} | {document_set.topic}（已归档） | "
        f"[Design]({paths['design']}) | [PRD]({paths['prd']}) | "
        f"[Plan]({paths['plans']}) | [Acceptance]({paths['acceptance']}) |"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    ready = discover_ready_sets(args.repo_root)
    archived = archive_completed_sets(args.repo_root) if args.apply else ()
    print(
        json.dumps(
            {
                "archive_ready": [item.number for item in ready],
                "archived": list(archived),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
