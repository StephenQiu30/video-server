---
layer: Spec
spec_id: request-id
audience:
  - Dev
  - QA
purpose: "定义 request id 的生成、存储、传递和使用规范，确保请求追踪的完整性和一致性。"
canonical_path: "openspec/changes/global-response-error-handling/specs/request-id/spec.md"
status: draft
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/07-全局响应格式与异常处理.md"
  - "apps/api/app/middleware/request_context.py"
outputs:
  - "Request ID 规范"
triggers:
  - "调整 request id 生成逻辑"
  - "修改 request id 传递方式"
---

# Spec: request-id

## 1. Request ID 生命周期

### 1.1 生成

**来源优先级**：

1. 客户端传入的 `X-Request-ID` 请求头
2. 自动生成的 UUID（`uuid4().hex`）

**实现**：

```python
request_id = request.headers.get("X-Request-ID") or uuid4().hex
```

**约束**：
- 客户端传入的 `X-Request-ID` 必须是非空字符串
- 自动生成的 UUID 使用 `uuid4().hex` 格式（32 位十六进制，无连字符）

### 1.2 存储

**存储位置**：`request.state.request_id`

**实现**：

```python
request.state.request_id = request_id
```

**约束**：
- 必须在 `call_next` 之前存储
- 存储后可在整个请求生命周期内访问

### 1.3 传递

**响应头**：`X-Request-ID`

**实现**：

```python
response.headers["X-Request-ID"] = request_id
```

**约束**：
- 所有响应必须包含 `X-Request-ID` 响应头
- 响应头值必须与请求处理使用的 request_id 一致

### 1.4 错误响应包含

**位置**：`error.request_id`

**实现**：

```python
failure_response(code, message, details, request_id)
```

**约束**：
- 所有错误响应必须包含 `request_id` 字段
- `request_id` 位于 `error` 对象内

## 2. 使用场景

### 2.1 异常处理

所有 exception handler 必须从 `request.state` 获取 `request_id`：

```python
request_id = getattr(request.state, "request_id", None)
```

### 2.2 日志记录

异常日志必须包含 `request_id`：

```python
logger.exception(
    "Unhandled API exception path=%s method=%s request_id=%s",
    request.url.path,
    request.method,
    request_id,
    exc_info=exc,
)
```

### 2.3 业务逻辑

业务逻辑可通过 `request.state.request_id` 访问 request_id，用于日志记录或追踪。

## 3. 实现要求

### 3.1 Middleware 修改

**文件**：`apps/api/app/middleware/request_context.py`

**变更**：

```python
async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id  # 新增
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Request-Duration-Ms"] = str(duration_ms)
    return response
```

### 3.2 约束

- 不得修改 request_id 生成逻辑
- 不得修改响应头设置逻辑
- 不得在 request_id 中包含敏感信息
