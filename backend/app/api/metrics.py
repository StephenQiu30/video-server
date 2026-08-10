"""Authenticated internal low-cardinality Prometheus metrics."""

from datetime import UTC, datetime
from hmac import compare_digest

from fastapi import APIRouter, Header, Request
from fastapi.responses import PlainTextResponse

from app.core.errors import AppError
from app.infrastructure.operational_metrics import OperationalMetrics

router = APIRouter()


@router.get("/internal/metrics", include_in_schema=False)
async def metrics(
    request: Request,
    x_metrics_key: str | None = Header(default=None, alias="X-Metrics-Key"),
) -> PlainTextResponse:
    expected = request.app.state.settings.metrics_access_key.get_secret_value()
    if x_metrics_key is None or not compare_digest(x_metrics_key, expected):
        raise AppError(
            status=404,
            code="not_found",
            title="Not found",
            detail="The requested resource was not found.",
        )
    collector: OperationalMetrics | None = getattr(
        request.app.state, "operational_metrics", None
    )
    if collector is None:
        raise AppError(
            status=503,
            code="metrics_unavailable",
            title="Metrics unavailable",
            detail="Operational metrics are not available.",
        )
    return PlainTextResponse(
        await collector.render(datetime.now(UTC)),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
