"""Transport mapping for application admission failures."""

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.exception_handlers import app_error_handler
from app.services.quotas import QuotaExceeded


async def quota_error_handler(request: Request, error: Exception) -> JSONResponse:
    quota = cast(QuotaExceeded, error)
    details = {
        "active_task_quota_exceeded": "Wait for active tasks to finish or cancel them.",
        "daily_task_quota_exceeded": "The rolling 24-hour task budget is exhausted.",
        "daily_byte_quota_exceeded": "The rolling 24-hour byte budget is exhausted.",
        "analysis_budget_exceeded": "The rolling 24-hour analysis budget is exhausted.",
        "storage_quota_exceeded": (
            "Delete retained files or finish active tasks to free space."
        ),
    }
    return await app_error_handler(
        request,
        AppError(
            status=429,
            code=quota.code,
            title="Resource budget exceeded",
            detail=details[quota.code],
            headers={"Retry-After": str(quota.retry_after)},
        ),
    )
