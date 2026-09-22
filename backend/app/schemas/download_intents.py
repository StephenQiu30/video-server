from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import StrictModel
from app.services.downloads.intent_models import IntentSnapshot, IntentStatus


class IntentRequest(StrictModel):
    input: str = Field(
        min_length=8,
        max_length=4096,
        description="公开媒体地址或包含唯一媒体地址的分享文案。",
    )


class IntentResponse(StrictModel):
    id: UUID
    version: int
    status: IntentStatus
    reason_code: str | None
    next_action: Literal["none"] = "none"
    retry_at: datetime | None
    deadline: datetime
    inspection_id: UUID | None
    job_id: UUID | None

    @classmethod
    def from_snapshot(cls, value: IntentSnapshot) -> "IntentResponse":
        return cls(
            id=value.id,
            version=value.version,
            status=value.status,
            reason_code=value.reason_code,
            retry_at=value.retry_at,
            deadline=value.deadline,
            inspection_id=value.inspection_id,
            job_id=value.job_id,
        )
