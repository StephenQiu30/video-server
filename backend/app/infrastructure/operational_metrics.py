from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisResultRow,
    AnalysisRunRow,
    OperationalCounterRow,
    OutboxEventRow,
)

_COUNTERS = (
    ("claim_noop", "analysis"),
    ("claim_noop", "report"),
    ("outbox_confirm", "ack"),
    ("outbox_confirm", "failed"),
)
_OUTBOX_EVENT_TYPES = (
    "download.requested",
    "analysis.requested",
    "analysis.report.publish.requested",
    "task.state.changed",
)
_ANALYSIS_STATES = (
    "queued",
    "running",
    "retry_wait",
    "succeeded",
    "failed",
    "cancelled",
)
_REPORT_STATES = (
    "validated",
    "publishing",
    "available",
    "publish_failed",
    "delete_pending",
    "deleted",
)


class OperationalMetrics:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def render(self, now: datetime) -> str:
        async with self._sessions() as session:
            lines = await self._counters(session)
            lines += await self._outbox(session, now)
            lines += await self._analyses(session, now)
            lines += await self._reports(session)
        return "\n".join(sorted(lines)) + "\n"

    @staticmethod
    async def _counters(session: AsyncSession) -> list[str]:
        rows = (await session.execute(select(OperationalCounterRow))).scalars().all()
        values = {(row.metric, row.dimension): row.value for row in rows}
        return [
            f'video_{metric}_total{{result="{dimension}"}} '
            f"{values.get((metric, dimension), 0)}"
            for metric, dimension in _COUNTERS
        ]

    @staticmethod
    async def _outbox(session: AsyncSession, now: datetime) -> list[str]:
        rows = (
            await session.execute(
                select(
                    OutboxEventRow.event_type,
                    func.count(),
                    func.min(OutboxEventRow.created_at),
                )
                .where(OutboxEventRow.published_at.is_(None))
                .group_by(OutboxEventRow.event_type)
            )
        ).all()
        values = {event_type: (count, oldest) for event_type, count, oldest in rows}
        lines: list[str] = []
        for event_type in _OUTBOX_EVENT_TYPES:
            count, oldest = values.get(event_type, (0, None))
            age = (
                max(0.0, (as_utc(now) - as_utc(oldest)).total_seconds())
                if oldest is not None
                else 0.0
            )
            lines.append(
                f'video_outbox_unpublished{{event_type="{event_type}"}} {count}'
            )
            lines.append(
                f'video_outbox_oldest_seconds{{event_type="{event_type}"}} {age:.3f}'
            )
        return lines

    @staticmethod
    async def _analyses(session: AsyncSession, now: datetime) -> list[str]:
        states = (
            await session.execute(
                select(AnalysisJobRow.status, func.count())
                .where(AnalysisJobRow.deleted_at.is_(None))
                .group_by(AnalysisJobRow.status)
            )
        ).all()
        expired = await session.scalar(
            select(func.count())
            .select_from(AnalysisJobRow)
            .where(
                AnalysisJobRow.status == "running",
                AnalysisJobRow.lease_expires_at <= now,
            )
        )
        retries = await session.scalar(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (AnalysisRunRow.attempt > 1, AnalysisRunRow.attempt - 1),
                            else_=0,
                        )
                    ),
                    0,
                )
            )
        )
        counts: dict[str, int] = {str(state): int(count) for state, count in states}
        return [
            *(
                f'video_analysis_jobs{{state="{state}"}} {counts.get(state, 0)}'
                for state in _ANALYSIS_STATES
            ),
            f"video_analysis_expired_leases {int(expired or 0)}",
            f"video_analysis_technical_retries_total {int(retries or 0)}",
        ]

    @staticmethod
    async def _reports(session: AsyncSession) -> list[str]:
        rows = (
            await session.execute(
                select(AnalysisResultRow.status, func.count()).group_by(
                    AnalysisResultRow.status
                )
            )
        ).all()
        counts: dict[str, int] = {str(state): int(count) for state, count in rows}
        return [
            f'video_analysis_reports{{state="{state}"}} {counts.get(state, 0)}'
            for state in _REPORT_STATES
        ]
