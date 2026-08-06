from typing import Literal

from app.api.schemas.common import StrictModel


class LivenessResponse(StrictModel):
    status: Literal["ok"]


class ReadinessResponse(StrictModel):
    status: Literal["ok", "unavailable"]
    service: Literal["api"]
