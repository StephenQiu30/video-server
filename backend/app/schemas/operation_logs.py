from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import StrictModel

OperationOutcome = Literal["started", "succeeded", "failed"]


class OperationLogResponse(StrictModel):
    id: UUID
    created_at: datetime
    finished_at: datetime | None
    actor_id: UUID | None
    actor_name: str | None
    operation: str
    description: str
    method: str
    route: str
    resource_id: UUID | None
    resource_key: str | None
    outcome: OperationOutcome
    source: Literal["request", "task"]
    task_state: str | None
    status_code: int | None
    error_code: str | None


class OperationLogPageResponse(StrictModel):
    items: list[OperationLogResponse]
    page: int
    page_size: int
    total: int
