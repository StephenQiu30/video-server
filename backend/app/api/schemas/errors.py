from pydantic import Field

from app.api.schemas.common import StrictModel


class ProblemDetails(StrictModel):
    """RFC 9457 error document returned by public API operations."""

    type: str = Field(description="稳定的服务错误类型 URI。")
    title: str = Field(description="面向调用方的简短错误标题。")
    status: int = Field(description="HTTP 状态码。")
    detail: str = Field(description="不包含敏感信息的错误说明。")
    code: str = Field(description="供客户端分支处理的稳定错误码。")
    instance: str = Field(description="产生错误的请求路径。")
