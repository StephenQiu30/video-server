from enum import StrEnum
from typing import Literal

from app.schemas.common import StrictModel


class LivenessStatus(StrEnum):
    OK = "ok"


class ReadinessStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class LivenessResponse(StrictModel):
    status: LivenessStatus


class ReadinessResponse(StrictModel):
    status: ReadinessStatus
    service: Literal["api"]
