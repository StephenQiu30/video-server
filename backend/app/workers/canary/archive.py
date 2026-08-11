"""Archive accepted 017 documents after the live Provider gate passes."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.workers.canary.archive_ready import pending_provider_statuses
from app.workers.canary.document_archive import (
    DocumentArchiveError,
    archive_017_documents,
    validate_017_documents,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive the accepted 017 document set after live verification."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="move documents; without this flag the command only checks readiness",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
    )
    return parser


async def _run(*, apply: bool, repo_root: Path) -> int:
    pending = await pending_provider_statuses()
    if pending:
        _print_result(archive_ready=False, archived=False, pending=pending)
        return 1
    try:
        if not apply:
            paths = validate_017_documents(repo_root)
            _print_result(
                archive_ready=True,
                archived=False,
                pending=(),
                paths=paths,
            )
            return 0
        result = archive_017_documents(repo_root)
    except DocumentArchiveError as error:
        _print_result(
            archive_ready=False,
            archived=False,
            pending=(),
            error=str(error),
        )
        return 1
    except OSError:
        _print_result(
            archive_ready=False,
            archived=False,
            pending=(),
            error="document_archive_io_failed",
        )
        return 1
    _print_result(
        archive_ready=True,
        archived=result.archived,
        pending=(),
        paths=result.paths,
    )
    return 0


def _print_result(
    *,
    archive_ready: bool,
    archived: bool,
    pending: tuple[dict[str, str], ...],
    error: str | None = None,
    paths: tuple[str, ...] = (),
) -> None:
    payload: dict[str, object] = {
        "archive_ready": archive_ready,
        "archived": archived,
        "pending": pending,
    }
    if error is not None:
        payload["error"] = error
    if paths:
        payload["paths"] = paths
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_run(apply=args.apply, repo_root=args.repo_root)))


if __name__ == "__main__":
    main()
