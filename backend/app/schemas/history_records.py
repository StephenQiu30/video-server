from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import StrictModel
from app.schemas.download_intents import IntentHistoryItemResponse
from app.services.analysis.rules.enums import (
    AnalysisErrorCode,
    AnalysisStage,
    AnalysisStatus,
)
from app.services.downloads.intent_models import IntentStatus
from app.services.history_records import (
    HistoryRecordCursor,
    HistoryRecordKind,
    HistoryRecordPage,
    HistoryRecordSnapshot,
)


class HistoryRecordCursorResponse(StrictModel):
    created_at: datetime
    record_type: HistoryRecordKind
    id: UUID

    @classmethod
    def from_cursor(cls, cursor: HistoryRecordCursor) -> "HistoryRecordCursorResponse":
        return cls(
            created_at=cursor.created_at,
            record_type=cursor.record_type,
            id=cursor.id,
        )


class ParseHistoryRecordResponse(IntentHistoryItemResponse):
    record_type: Literal["parse"]


class VideoAnalysisHistoryRecordResponse(StrictModel):
    record_type: Literal["video_analysis"]
    id: UUID
    download_id: UUID | None
    title: str
    skill_id: str
    created_at: datetime
    status: AnalysisStatus
    progress: int
    stage: AnalysisStage | None
    error_code: AnalysisErrorCode | None


HistoryRecordItemResponse = Annotated[
    ParseHistoryRecordResponse | VideoAnalysisHistoryRecordResponse,
    Field(discriminator="record_type"),
]


class HistoryRecordPageResponse(StrictModel):
    items: list[HistoryRecordItemResponse]
    next_cursor: HistoryRecordCursorResponse | None

    @classmethod
    def from_page(cls, page: HistoryRecordPage) -> "HistoryRecordPageResponse":
        items: list[HistoryRecordItemResponse] = []
        for item in page.items:
            if item.record_type is HistoryRecordKind.PARSE:
                items.append(_parse_item(item))
            else:
                items.append(_analysis_item(item))
        return cls(
            items=items,
            next_cursor=(
                None
                if page.next_cursor is None
                else HistoryRecordCursorResponse.from_cursor(page.next_cursor)
            ),
        )


def _parse_item(item: HistoryRecordSnapshot) -> ParseHistoryRecordResponse:
    if item.version is None or item.deadline is None:
        raise ValueError("parse history record is incomplete")
    return ParseHistoryRecordResponse(
        record_type="parse",
        id=item.id,
        version=item.version,
        status=IntentStatus(item.status),
        reason_code=item.reason_code,
        retry_at=item.retry_at,
        deadline=item.deadline,
        inspection_id=item.inspection_id,
        job_id=item.job_id,
        created_at=item.created_at,
        title=item.title,
    )


def _analysis_item(item: HistoryRecordSnapshot) -> VideoAnalysisHistoryRecordResponse:
    if item.skill_id is None or item.progress is None:
        raise ValueError("video analysis history record is incomplete")
    return VideoAnalysisHistoryRecordResponse(
        record_type="video_analysis",
        id=item.id,
        download_id=item.download_id,
        title=item.title,
        skill_id=item.skill_id,
        created_at=item.created_at,
        status=AnalysisStatus(item.status),
        progress=item.progress,
        stage=None if item.stage is None else AnalysisStage(item.stage),
        error_code=(
            None if item.error_code is None else AnalysisErrorCode(item.error_code)
        ),
    )
