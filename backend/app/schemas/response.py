"""The public Web JSON response envelope."""

from pydantic import Field

from app.core.error_codes import ErrorCode
from app.schemas.common import StrictModel


class ApiResponse[T](StrictModel):
    code: ErrorCode = Field(description="稳定的业务结果码。")
    message: str = Field(description="安全的结果说明。")
    data: T = Field(description="成功时为业务数据，错误时为 null。")


class ErrorResponse(ApiResponse[None]):
    data: None
