from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.admission import RateLimitAdmission
from app.api.auth_dependencies import get_current_user
from app.api.dependencies import (
    DownloadUseCases,
    IdempotencyKey,
    get_download_storage,
    get_download_use_cases,
    get_runtime_settings,
)
from app.api.errors import application_error
from app.api.schemas.downloads import (
    DownloadRequest,
    DownloadResponse,
    DownloadUrlResponse,
)
from app.api.schemas.history import DownloadHistoryResponse
from app.api.upload_signing import use_browser_download_proxy
from app.application.auth import CurrentUser
from app.application.downloads import (
    ApplicationError,
    ArtifactSnapshot,
    DownloadArtifactStorage,
    DownloadView,
    download_disposition,
)
from app.domain.downloads import DownloadStatus

router = APIRouter(prefix="/downloads", tags=["downloads"])
User = Annotated[CurrentUser, Depends(get_current_user)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]
DownloadStorage = Annotated[DownloadArtifactStorage, Depends(get_download_storage)]


@router.post(
    "",
    operation_id="createDownload",
    dependencies=[Depends(RateLimitAdmission("download"))],
    response_model=DownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建下载任务",
)
async def create_download(
    body: DownloadRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """根据解析结果和语义格式创建异步下载任务。"""
    try:
        view = await use_cases.create_download(
            body.inspection_id,
            body.format_id,
            user.owner_hash,
            idempotency_key,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    response.headers["Location"] = f"/api/downloads/{view.id}"
    return DownloadResponse.from_view(view)


@router.delete(
    "/{job_id}",
    operation_id="deleteDownload",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除下载任务及其私有文件",
)
async def delete_download(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """删除当前用户的任务、下载制品、本地上传源文件与私有封面。"""
    try:
        await use_cases.delete_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/history",
    operation_id="getDownloadHistory",
    response_model=DownloadHistoryResponse,
    summary="查询下载历史",
)
async def get_download_history(
    user: User,
    use_cases: UseCases,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    status_filter: Annotated[DownloadStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=128)] = None,
) -> DownloadHistoryResponse:
    """查询当前登录用户的下载历史。"""
    try:
        view = await use_cases.get_download_history(
            user.owner_hash,
            page=page,
            page_size=page_size,
            status=status_filter,
            search=search,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadHistoryResponse.from_view(view)


@router.get(
    "/{job_id}/thumbnail",
    operation_id="getDownloadThumbnail",
    response_class=Response,
    responses={
        200: {
            "description": "Private persisted download thumbnail",
            "content": {
                "image/avif": {},
                "image/jpeg": {},
                "image/png": {},
                "image/webp": {},
            },
        }
    },
    summary="读取下载任务封面",
)
async def get_download_thumbnail(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> Response:
    """读取当前用户本地导入视频生成的私有首帧封面。"""
    try:
        thumbnail = await use_cases.get_download_thumbnail(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return Response(
        content=thumbnail.content,
        media_type=thumbnail.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "ETag": f'"{thumbnail.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _owned_download_file(
    job_id: UUID,
    user: CurrentUser,
    use_cases: DownloadUseCases,
) -> tuple[ArtifactSnapshot, DownloadView]:
    try:
        artifact = await use_cases.get_download_artifact(job_id, user.owner_hash)
        download = await use_cases.get_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return artifact, download


def _download_file_response(
    artifact: ArtifactSnapshot,
    download: DownloadView,
    *,
    preview: bool,
    range_header: str | None,
) -> tuple[int, int, int, dict[str, str]] | Response:
    selected_range = _parse_range(range_header, artifact.size_bytes)
    if range_header is not None and selected_range is None:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{artifact.size_bytes}"},
        )

    if selected_range is None:
        start, end = 0, artifact.size_bytes - 1
        response_status = status.HTTP_200_OK
    else:
        start, end = selected_range
        response_status = status.HTTP_206_PARTIAL_CONTENT
    length = end - start + 1
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-store",
        "Content-Disposition": (
            "inline"
            if preview
            else download_disposition(artifact.object_key, download.title)
        ),
        "Content-Length": str(length),
        "ETag": f'"{artifact.sha256}"',
    }
    if selected_range is not None:
        headers["Content-Range"] = f"bytes {start}-{end}/{artifact.size_bytes}"
    return start, end, response_status, headers


@router.head(
    "/{job_id}/file",
    operation_id="inspectDownloadFile",
    response_class=Response,
    summary="读取已完成视频文件元数据",
)
async def inspect_download_file(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
    preview: bool = False,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    """Return owned artifact headers without streaming its body."""
    artifact, download = await _owned_download_file(job_id, user, use_cases)
    selection = _download_file_response(
        artifact,
        download,
        preview=preview,
        range_header=range_header,
    )
    if isinstance(selection, Response):
        return selection
    _start, _end, response_status, headers = selection
    return Response(
        status_code=response_status,
        headers=headers,
        media_type=artifact.content_type,
    )


@router.get(
    "/{job_id}/file",
    operation_id="downloadFile",
    response_class=StreamingResponse,
    summary="读取已完成的视频文件",
)
async def download_file(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
    storage: DownloadStorage,
    preview: bool = False,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    """Stream an owned artifact through the authenticated application origin."""
    artifact, download = await _owned_download_file(job_id, user, use_cases)
    selection = _download_file_response(
        artifact,
        download,
        preview=preview,
        range_header=range_header,
    )
    if isinstance(selection, Response):
        return selection
    start, end, response_status, headers = selection
    length = end - start + 1
    return StreamingResponse(
        storage.iter_download(
            artifact.object_key,
            offset=start,
            length=length,
        ),
        status_code=response_status,
        headers=headers,
        media_type=artifact.content_type,
    )


@router.get(
    "/{job_id}",
    operation_id="getDownload",
    response_model=DownloadResponse,
    summary="查询下载任务",
)
async def get_download(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """查询当前登录用户拥有的下载任务。"""
    try:
        view = await use_cases.get_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post(
    "/{job_id}/cancel",
    operation_id="cancelDownload",
    response_model=DownloadResponse,
    summary="取消下载任务",
)
async def cancel_download(
    job_id: UUID,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """请求取消尚未结束的下载任务。"""
    try:
        view = await use_cases.cancel_download(job_id, user.owner_hash)
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadResponse.from_view(view)


@router.post(
    "/{job_id}/retry",
    operation_id="retryDownload",
    dependencies=[Depends(RateLimitAdmission("download_retry"))],
    response_model=DownloadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="重试下载任务",
)
async def retry_download(
    job_id: UUID,
    idempotency_key: IdempotencyKey,
    response: Response,
    user: User,
    use_cases: UseCases,
) -> DownloadResponse:
    """从失败或已取消的任务创建一条新的下载任务。"""
    try:
        view = await use_cases.retry_download(
            job_id,
            user.owner_hash,
            idempotency_key,
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    response.headers["Location"] = f"/api/downloads/{view.id}"
    return DownloadResponse.from_view(view)


@router.post(
    "/{job_id}/download-url",
    operation_id="issueDownloadUrl",
    response_model=DownloadUrlResponse,
    summary="签发文件下载地址",
)
async def issue_download_url(
    job_id: UUID,
    request: Request,
    user: User,
    use_cases: UseCases,
    preview: bool = False,
) -> DownloadUrlResponse:
    """为已完成的下载任务签发短时制品地址。"""
    try:
        view = await use_cases.issue_download_url(
            job_id,
            user.owner_hash,
            preview=preview,
            use_browser_proxy=use_browser_download_proxy(
                request, get_runtime_settings(request)
            ),
        )
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadUrlResponse.from_view(view)


def _parse_range(
    value: str | None,
    size: int,
) -> tuple[int, int] | None:
    if value is None:
        return None
    if size < 1 or not value.startswith("bytes=") or "," in value:
        return None
    start_text, separator, end_text = value.removeprefix("bytes=").partition("-")
    if not separator:
        return None
    try:
        if not start_text:
            suffix_length = int(end_text)
            if suffix_length < 1:
                return None
            start = max(0, size - suffix_length)
            return start, size - 1
        start = int(start_text)
        end = size - 1 if not end_text else int(end_text)
    except ValueError:
        return None
    if start < 0 or start >= size or end < start:
        return None
    return start, min(end, size - 1)
