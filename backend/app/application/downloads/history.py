from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.application.downloads.errors import ApplicationError, ApplicationErrorCode
from app.application.downloads.history_models import (
    DownloadHistoryItemSnapshot,
    DownloadHistoryItemView,
    DownloadHistoryPageSnapshot,
    DownloadHistorySummaryView,
    DownloadHistoryView,
)
from app.application.downloads.ports import DownloadRepository
from app.application.downloads.thumbnail import thumbnail_resource_url
from app.application.downloads.validation import validate_now, validate_owner_hash
from app.domain.downloads import DownloadErrorCode, DownloadSourceKind, DownloadStatus


class GetDownloadHistory:
    def __init__(
        self, repository: DownloadRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(
        self,
        owner_hash: str,
        *,
        page: int = 1,
        page_size: int = 20,
        status: DownloadStatus | None = None,
        search: str | None = None,
    ) -> DownloadHistoryView:
        if not 1 <= page <= 10_000 or not 1 <= page_size <= 50:
            raise ApplicationError(ApplicationErrorCode.INVALID_REQUEST)
        normalized_search = search.strip() if search else None
        if normalized_search and len(normalized_search) > 128:
            raise ApplicationError(ApplicationErrorCode.INVALID_REQUEST)
        snapshot = await self._repository.list_download_history(
            validate_owner_hash(owner_hash),
            page=page,
            page_size=page_size,
            status=None if status is None else status.value,
            search=normalized_search or None,
            now=validate_now(self._now()),
        )
        return _history_view(snapshot)


def _history_view(snapshot: DownloadHistoryPageSnapshot) -> DownloadHistoryView:
    try:
        items = tuple(_item_view(item) for item in snapshot.items)
    except ValueError as exc:
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
    return DownloadHistoryView(
        items=items,
        page=snapshot.page,
        page_size=snapshot.page_size,
        total=snapshot.total,
        summary=DownloadHistorySummaryView(
            total=snapshot.summary.total,
            succeeded=snapshot.summary.succeeded,
            active=snapshot.summary.active,
            failed=snapshot.summary.failed,
        ),
    )


def _item_view(item: DownloadHistoryItemSnapshot) -> DownloadHistoryItemView:
    source_kind = DownloadSourceKind(item.source_kind)
    return DownloadHistoryItemView(
        id=item.id,
        title=item.title or "未命名视频",
        thumbnail_url=(
            thumbnail_resource_url(item.inspection_id)
            if item.thumbnail_available and item.inspection_id is not None
            else None
        ),
        format_name=item.format_name,
        status=DownloadStatus(item.status),
        progress=item.progress,
        error_code=(
            DownloadErrorCode(item.error_code) if item.error_code is not None else None
        ),
        created_at=item.created_at,
        updated_at=item.updated_at,
        finished_at=item.finished_at,
        file_available=item.file_available,
        source_kind=source_kind,
        source_label=(
            (
                "用户提供的视频号来源文件"
                if item.declared_origin == "wechat_channels"
                else "本地视频上传"
            )
            if source_kind is DownloadSourceKind.BROWSER_IMPORT
            else "链接下载"
        ),
    )
