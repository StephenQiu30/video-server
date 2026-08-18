from __future__ import annotations

from typing import Any

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.storage_files import StoredFilePage, StoredFileView
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisReportArtifactRow,
    AnalysisReportVersionRow,
    ArtifactRow,
    DocumentArtifactRow,
    DocumentRow,
    DownloadJobRow,
    MediaImportRow,
    MediaInspectionRow,
)


async def list_stored_files(
    sessions: async_sessionmaker[AsyncSession], *, page: int, page_size: int
) -> StoredFilePage:
    files = _stored_files_statement().subquery()
    async with sessions() as session:
        total = await session.scalar(select(func.count()).select_from(files))
        rows = (
            await session.execute(
                select(files)
                .order_by(files.c.created_at.desc(), files.c.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).mappings()
        return StoredFilePage(
            items=tuple(
                StoredFileView(
                    id=row["id"],
                    category=row["category"],
                    name=row["name"],
                    object_count=int(row["object_count"]),
                    size_bytes=int(row["size_bytes"]),
                    created_at=as_utc(row["created_at"]),
                )
                for row in rows
            ),
            page=page,
            page_size=page_size,
            total=int(total or 0),
        )


def _stored_files_statement() -> Any:
    video_name = func.coalesce(
        MediaImportRow.display_name,
        MediaInspectionRow.title,
        literal("视频文件"),
    )
    videos = (
        select(
            ArtifactRow.id.label("id"),
            literal("video").label("category"),
            video_name.label("name"),
            literal(1).label("object_count"),
            ArtifactRow.size_bytes.label("size_bytes"),
            ArtifactRow.created_at.label("created_at"),
        )
        .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
        .outerjoin(
            MediaInspectionRow,
            MediaInspectionRow.id == DownloadJobRow.inspection_id,
        )
        .outerjoin(MediaImportRow, MediaImportRow.id == DownloadJobRow.id)
        .where(ArtifactRow.deleted_at.is_(None))
    )
    documents = (
        select(
            DocumentRow.id.label("id"),
            literal("screenplay").label("category"),
            DocumentRow.title.label("name"),
            func.count(DocumentArtifactRow.id).label("object_count"),
            func.sum(DocumentArtifactRow.size_bytes).label("size_bytes"),
            DocumentRow.created_at.label("created_at"),
        )
        .join(DocumentArtifactRow, DocumentArtifactRow.document_id == DocumentRow.id)
        .where(
            DocumentRow.deleted_at.is_(None),
            DocumentRow.status == "ready",
            DocumentArtifactRow.status == "ready",
            DocumentArtifactRow.deleted_at.is_(None),
        )
        .group_by(DocumentRow.id, DocumentRow.title, DocumentRow.created_at)
    )
    reports = (
        select(
            AnalysisReportVersionRow.id.label("id"),
            literal("analysis_report").label("category"),
            literal("分析报告").label("name"),
            func.count(AnalysisReportArtifactRow.id).label("object_count"),
            func.sum(AnalysisReportArtifactRow.size_bytes).label("size_bytes"),
            AnalysisReportVersionRow.created_at.label("created_at"),
        )
        .join(
            AnalysisReportArtifactRow,
            AnalysisReportArtifactRow.report_id == AnalysisReportVersionRow.id,
        )
        .where(
            AnalysisReportVersionRow.status == "available",
            AnalysisReportArtifactRow.status == "available",
            AnalysisReportArtifactRow.deleted_at.is_(None),
        )
        .group_by(AnalysisReportVersionRow.id, AnalysisReportVersionRow.created_at)
    )
    return union_all(videos, documents, reports)
