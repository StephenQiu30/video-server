from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.auth_dependencies import get_current_admin
from app.api.dependencies import DownloadUseCases, get_download_use_cases
from app.api.errors import application_error, auth_application_error
from app.api.schemas.admin_downloads import DownloadAnalyticsResponse
from app.application.auth import AuthError, CurrentUser
from app.application.downloads import ApplicationError

router = APIRouter(prefix="/admin/downloads", tags=["admin"])
Admin = Annotated[CurrentUser, Depends(get_current_admin)]
UseCases = Annotated[DownloadUseCases, Depends(get_download_use_cases)]


@router.get(
    "/analytics",
    operation_id="getDownloadAnalytics",
    response_model=DownloadAnalyticsResponse,
    summary="查询下载分析",
)
async def get_download_analytics(
    admin: Admin,
    use_cases: UseCases,
    days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> DownloadAnalyticsResponse:
    """按 UTC 自然日查询管理员可见的全局下载聚合。"""
    try:
        view = await use_cases.get_download_analytics(admin, days=days)
    except AuthError as exc:
        raise auth_application_error(exc) from exc
    except ApplicationError as exc:
        raise application_error(exc) from exc
    return DownloadAnalyticsResponse.from_view(view)
