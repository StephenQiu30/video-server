---
layer: Spec
spec_id: global-error-model
audience:
  - Dev
  - QA
purpose: "定义全局错误模型规范，覆盖 failure envelope 结构、错误码分类、成功响应迁移原则。"
canonical_path: "openspec/changes/global-response-error-handling/specs/global-error-model/spec.md"
status: draft
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/07-全局响应格式与异常处理.md"
outputs:
  - "全局错误模型规范"
triggers:
  - "新增错误码"
  - "调整 failure envelope 结构"
---

# Spec: global-error-model

## 1. Failure Envelope 结构

所有错误响应必须遵循以下结构：

```json
{
  "success": false,
  "error": {
    "code": "error_code",
    "message": "用户可读的错误描述",
    "details": {},
    "request_id": "abc123"
  }
}
```

### 字段定义

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `success` | boolean | 是 | 固定为 `false` |
| `error` | object | 是 | 错误详情对象 |
| `error.code` | string | 是 | 机器可读错误码，使用 snake_case |
| `error.message` | string | 是 | 用户可读的错误描述，中文 |
| `error.details` | object/array/null | 否 | 额外错误详情，用于参数校验等场景 |
| `error.request_id` | string | 是 | 请求追踪 ID，来自 `X-Request-ID` |

## 2. 错误码分类

| 分类 | 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- | --- |
| 入口校验 | `invalid_url` | 400 | URL 格式错误 |
| 入口校验 | `unsafe_url` | 400 | URL 不安全（SSRF 风险） |
| 平台相关 | `parse_failed` | 400 | 平台解析失败 |
| 平台相关 | `platform_restricted` | 403 | 平台限制 |
| 平台相关 | `platform_rate_limited` | 429 | 平台限流 |
| 平台相关 | `unsupported_platform` | 400 | 不支持的平台 |
| 平台相关 | `platform_unavailable` | 503 | 平台不可用 |
| 基础设施 | `engine_unavailable` | 503 | 下载引擎不可用 |
| 基础设施 | `queue_unavailable` | 503 | 队列不可用 |
| 基础设施 | `storage_unavailable` | 503 | 存储不可用 |
| 认证授权 | `invalid_credentials` | 401 | 凭据错误 |
| 认证授权 | `user_disabled` | 403 | 用户已禁用 |
| 认证授权 | `auth_locked` | 403 | 认证锁定 |
| 认证授权 | `registration_disabled` | 403 | 注册未开放 |
| 认证授权 | `registration_failed` | 400 | 注册失败 |
| 任务生命周期 | `invalid_state` | 409/422 | 状态无效 |
| 任务生命周期 | `limit_exceeded` | 429 | 超出限制 |
| 任务生命周期 | `not_found` | 404 | 资源不存在 |
| 任务生命周期 | `retention_expired` | 410 | 保留时间已过期 |
| 任务生命周期 | `retry_superseded` | 409 | 重试已被取代 |
| 通用 | `rate_limited` | 429 | 请求限流 |
| 通用 | `validation_error` | 422 | 参数校验错误 |
| 通用 | `internal_error` | 500 | 内部错误 |

## 3. 成功响应迁移原则

### 向后兼容策略

1. 新接口必须使用统一 envelope：`{"success": true, "data": {...}}`
2. 已有接口保持原格式，不强制迁移
3. 后续可按需逐步迁移已有接口

### 统一成功 envelope 结构

```json
{
  "success": true,
  "data": {}
}
```

## 4. 实现要求

### 4.1 failure_response 函数

```python
def failure_response(code: str, message: str, details: Any = None, request_id: str | None = None) -> dict[str, Any]:
    error = {
        "code": code,
        "message": message,
        "details": details,
    }
    if request_id:
        error["request_id"] = request_id
    return {
        "success": False,
        "error": error,
    }
```

### 4.2 约束

- `error.code` 必须使用 snake_case
- `error.message` 必须是用户可读的中文描述
- `error.request_id` 必须包含在所有错误响应中
- 不得在 `error.details` 中暴露内部异常堆栈、token、cookie、secret、密码
