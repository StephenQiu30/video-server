## Context

video-server 后端使用 FastAPI 框架，已有初步的错误处理实现：

- **异常类**：`AppError` — 自定义业务异常，包含 `code`、`message`、`status_code`、`details`
- **错误码**：`ErrorCode` — StrEnum 枚举，分类定义错误码
- **响应格式**：`failure_response` — 生成统一错误响应结构
- **异常处理器**：
  - `app_error_handler` — 处理 `AppError`
  - `http_exception_handler` — 处理 `HTTPException` 和 `StarletteHTTPException`
  - `validation_exception_handler` — 处理 `RequestValidationError`
  - `unhandled_exception_handler` — 处理未知异常
- **Request Context**：`request_context_middleware` — 生成/提取 request_id，添加响应头

**当前缺失：**

1. request_id 未存储到 `request.state`，exception handler 无法访问
2. 错误响应未包含 request_id
3. 缺少契约测试覆盖所有错误路径

## Goals / Non-Goals

**Goals:**

- 错误响应包含 request_id，支持问题追踪
- request_id 存储在 request.state 中，便于全局访问
- 所有异常类型遵循统一 failure envelope
- 契约测试覆盖所有错误路径

**Non-Goals:**

- 不迁移已有成功响应格式
- 不添加新的错误码
- 不修改日志脱敏规则（已实现基础脱敏）

## Decisions

### 1. Request ID 存储在 request.state

**选择**：在 `request_context_middleware` 中将 `request_id` 存储到 `request.state.request_id`。

**理由**：`request.state` 是 FastAPI/Starlette 提供的请求级状态存储，exception handler 可以通过 `request` 参数访问。

**替代方案**：
- 使用 contextvars：增加复杂度，且 exception handler 已有 `request` 参数
- 在 exception handler 中重新生成 request_id：丢失客户端传入的 request_id

### 2. failure_response 函数增加 request_id 参数

**选择**：`failure_response(code, message, details=None, request_id=None)`，request_id 默认值为 None。

**理由**：
- 保持向后兼容，已有调用无需修改
- 显式传递 request_id，避免函数内部访问 request.state（违反单一职责）

### 3. Exception handler 从 request.state 获取 request_id

**选择**：使用 `getattr(request.state, "request_id", None)` 安全访问。

**理由**：
- `request.state` 在某些异常场景下可能不存在属性
- 安全访问避免二次异常

### 4. 错误响应结构保持向后兼容

**选择**：在 `error` 对象中新增 `request_id` 字段，不修改已有字段。

**理由**：
- 已有客户端依赖 `success`、`error.code`、`error.message`、`error.details`
- 新增字段向后兼容，客户端可选择性使用

## Risks / Trade-offs

- **风险**：修改 `failure_response` 签名可能影响已有调用 → **缓解**：`request_id` 参数默认值为 `None`，保持向后兼容
- **风险**：`request.state` 在某些异常场景下可能不存在 → **缓解**：使用 `getattr` 安全访问
- **风险**：契约测试可能与实际实现不一致 → **缓解**：测试直接调用 exception handler，验证实际响应
