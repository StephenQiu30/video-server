"""Transport mapping for application admission failures."""

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from app.application.quotas import QuotaExceeded
from app.core.errors import AppError

from .errors import app_error_handler


async def quota_error_handler(request: Request, error: Exception) -> JSONResponse:
    quota = cast(QuotaExceeded, error)
    details = {
        "service_capacity_exceeded": "The service is at capacity. Try again later.",
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
            status=503 if quota.code == "service_capacity_exceeded" else 429,
            code=quota.code,
            title="Resource budget exceeded",
            detail=details[quota.code],
            headers={"Retry-After": str(quota.retry_after)},
        ),
    )
