"""Swagger UI and OpenAPI metadata for the public service contract."""

from typing import Any

from app.api.schemas.errors import ProblemDetails

API_DESCRIPTION = """
统一的视频下载与 AI 分析服务接口。

- 媒体解析、下载和分析均为异步任务，请通过对应查询接口获取进度。
- 创建媒体解析、下载或分析任务时必须提供 `Idempotency-Key` 请求头。
- 仅允许处理用户有权访问的公开、非 DRM HTTP(S) 媒体。
""".strip()

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "system",
        "description": "进程存活与运行依赖就绪状态。",
    },
    {
        "name": "inspections",
        "description": "校验媒体地址并解析可用的语义下载格式。",
    },
    {
        "name": "downloads",
        "description": "创建、查询、取消下载任务并签发制品地址。",
    },
    {
        "name": "analyses",
        "description": "创建、查询和取消视频 AI 分析任务。",
    },
]

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "displayRequestDuration": True,
    "filter": True,
    "operationsSorter": "method",
    "tagsSorter": "alpha",
}

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ProblemDetails, "description": "资源不存在或已经过期"},
    409: {"model": ProblemDetails, "description": "资源状态或幂等键冲突"},
    422: {"model": ProblemDetails, "description": "请求参数或业务输入无效"},
    500: {"model": ProblemDetails, "description": "服务内部错误"},
    502: {"model": ProblemDetails, "description": "上游媒体或模型服务失败"},
    503: {"model": ProblemDetails, "description": "运行依赖暂时不可用"},
    504: {"model": ProblemDetails, "description": "上游操作超时"},
}
