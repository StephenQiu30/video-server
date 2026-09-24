"""Unified read-only history over parse intents and video analysis jobs."""

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Uuid,
    and_,
    cast,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.analysis import AnalysisJobRow
from app.models.download import ArtifactRow, DownloadJobRow
from app.models.download_intent import DownloadIntentRow
from app.models.media import MediaInspectionRow
from app.models.media_import import MediaImportRow
from app.services.history_records import (
    HistoryRecordCursor,
    HistoryRecordKind,
    HistoryRecordPage,
    HistoryRecordSnapshot,
)


class SqlAlchemyHistoryRecordRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def history(
        self,
        owner_hash: str,
        *,
        before: HistoryRecordCursor | None,
        limit: int,
    ) -> HistoryRecordPage:
        intent_records = (
            select(
                literal(HistoryRecordKind.PARSE.value).label("record_type"),
                DownloadIntentRow.id.label("id"),
                func.coalesce(MediaInspectionRow.title, literal("媒体解析")).label(
                    "title"
                ),
                DownloadIntentRow.created_at.label("created_at"),
                DownloadIntentRow.status.label("status"),
                DownloadIntentRow.version.label("version"),
                DownloadIntentRow.reason_code.label("reason_code"),
                DownloadIntentRow.retry_at.label("retry_at"),
                DownloadIntentRow.deadline.label("deadline"),
                DownloadIntentRow.inspection_id.label("inspection_id"),
                DownloadIntentRow.job_id.label("job_id"),
                cast(null(), Uuid).label("download_id"),
                cast(null(), String).label("skill_id"),
                cast(null(), Integer).label("progress"),
                cast(null(), String).label("stage"),
                cast(null(), String).label("error_code"),
            )
            .outerjoin(
                MediaInspectionRow,
                and_(
                    MediaInspectionRow.id == DownloadIntentRow.inspection_id,
                    MediaInspectionRow.owner_hash == owner_hash,
                ),
            )
            .where(DownloadIntentRow.owner_hash == owner_hash)
        )
        analysis_records = (
            select(
                literal(HistoryRecordKind.VIDEO_ANALYSIS.value).label("record_type"),
                AnalysisJobRow.id.label("id"),
                func.coalesce(
                    MediaInspectionRow.title,
                    MediaImportRow.display_name,
                    literal("视频"),
                ).label("title"),
                AnalysisJobRow.created_at.label("created_at"),
                AnalysisJobRow.status.label("status"),
                cast(null(), Integer).label("version"),
                cast(null(), String).label("reason_code"),
                cast(null(), DateTime(timezone=True)).label("retry_at"),
                cast(null(), DateTime(timezone=True)).label("deadline"),
                cast(null(), Uuid).label("inspection_id"),
                cast(null(), Uuid).label("job_id"),
                DownloadJobRow.id.label("download_id"),
                AnalysisJobRow.skill_id.label("skill_id"),
                AnalysisJobRow.progress.label("progress"),
                AnalysisJobRow.stage.label("stage"),
                AnalysisJobRow.error_code.label("error_code"),
            )
            .outerjoin(ArtifactRow, ArtifactRow.id == AnalysisJobRow.artifact_id)
            .outerjoin(
                DownloadJobRow,
                and_(
                    DownloadJobRow.id == ArtifactRow.job_id,
                    DownloadJobRow.owner_hash == owner_hash,
                ),
            )
            .outerjoin(
                MediaInspectionRow,
                and_(
                    MediaInspectionRow.id == DownloadJobRow.inspection_id,
                    MediaInspectionRow.owner_hash == owner_hash,
                ),
            )
            .outerjoin(
                MediaImportRow,
                and_(
                    MediaImportRow.id == DownloadJobRow.id,
                    MediaImportRow.owner_hash == owner_hash,
                ),
            )
            .where(
                AnalysisJobRow.owner_hash == owner_hash,
                AnalysisJobRow.input_kind == "video",
                AnalysisJobRow.deleted_at.is_(None),
            )
        )
        records = union_all(intent_records, analysis_records).subquery(
            "history_records"
        )
        statement = select(records)
        if before is not None:
            statement = statement.where(
                or_(
                    records.c.created_at < before.created_at,
                    and_(
                        records.c.created_at == before.created_at,
                        records.c.id < before.id,
                    ),
                    and_(
                        records.c.created_at == before.created_at,
                        records.c.id == before.id,
                        records.c.record_type < before.record_type.value,
                    ),
                )
            )
        statement = statement.order_by(
            records.c.created_at.desc(),
            records.c.id.desc(),
            records.c.record_type.desc(),
        ).limit(limit + 1)

        async with self._sessions() as session:
            rows = (await session.execute(statement)).mappings().all()

        has_more = len(rows) > limit
        items = tuple(
            HistoryRecordSnapshot(
                id=row["id"],
                record_type=HistoryRecordKind(row["record_type"]),
                title=row["title"],
                created_at=row["created_at"],
                status=row["status"],
                version=row["version"],
                reason_code=row["reason_code"],
                retry_at=row["retry_at"],
                deadline=row["deadline"],
                inspection_id=row["inspection_id"],
                job_id=row["job_id"],
                download_id=row["download_id"],
                skill_id=row["skill_id"],
                progress=row["progress"],
                stage=row["stage"],
                error_code=row["error_code"],
            )
            for row in rows[:limit]
        )
        last = items[-1] if has_more and items else None
        cursor = (
            None
            if last is None
            else HistoryRecordCursor(last.created_at, last.record_type, last.id)
        )
        return HistoryRecordPage(items, cursor)
