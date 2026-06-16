---
layer: Spec
spec_id: exception-handlers
audience:
  - Dev
  - QA
purpose: "定义各类异常的处理方式和响应格式，确保所有异常遵循统一 failure envelope。"
canonical_path: "openspec/changes/global-response-error-handling/specs/exception-handlers/spec.md"
status: draft
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/07-全局响应格式与异常处理.md"
  - "apps/api/app/core/errors.py"
outputs:
  - "异常处理器规范"
triggers:
  - "新增异常类型"
  - "调整异常处理逻辑"
---

# Spec: exception-handlers

## 1. 异常处理分类

### 1.1 AppError 处理

**触发条件**：业务逻辑抛出 `AppError` 异常

**处理方式**：

```python
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=failure_response(exc.code, exc.message, exc.details, request_id),
    )
```

**响应格式**：

```json
{
  "success": false,
  "error": {
    "code": "app_error_code",
    "message": "业务错误描述",
    "details": {},
    "request_id": "abc123"
  }
}
```

**约束**：
- 使用 `exc.code` 作为 `error.code`
- 使用 `exc.message` 作为 `error.message`
- 使用 `exc.details` 作为 `error.details`
- 使用 `exc.status_code` 作为 HTTP 状态码

### 1.2 HTTPException 处理

**触发条件**：FastAPI 或 Starlette 抛出 `HTTPException`

**处理方式**：

```python
async def http_exception_handler(request: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    code, message = _http_error_contract(exc)
    return JSONResponse(status_code=exc.status_code, content=failure_response(code, message, request_id=request_id))
```

**错误码映射**：

| HTTP 状态码 | error.code | error.message |
| --- | --- | --- |
| 401 | `unauthorized` | 请先登录后再继续操作 |
| 403 | `forbidden` | 当前账号没有权限执行该操作 |
| 404 | `not_found` | 资源不存在 |
| 5xx | `internal_error` | 服务暂时不可用，请稍后重试 |
| 其他 | `http_error` | 原 detail 内容或 "请求处理失败" |

### 1.3 RequestValidationError 处理

**触发条件**：FastAPI 参数校验失败

**处理方式**：

```python
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=failure_response("validation_error", "请求参数不符合要求", exc.errors(), request_id),
    )
```

**响应格式**：

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "请求参数不符合要求",
    "details": [
      {
        "loc": ["body", "field_name"],
        "msg": "field required",
        "type": "value_error"
      }
    ],
    "request_id": "abc123"
  }
}
```

### 1.4 未知异常处理

**触发条件**：未被捕获的异常

**处理方式**：

```python
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled API exception path=%s method=%s request_id=%s",
        request.url.path,
        request.method,
        request_id,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=failure_response("internal_error", "服务暂时不可用，请稍后重试", request_id=request_id),
    )
```

**响应格式**：

```json
{
  "success": false,
  "error": {
    "code": "internal_error",
    "message": "服务暂时不可用，请稍后重试",
    "request_id": "abc123"
  }
}
```

**约束**：
- 不得在响应中暴露内部异常堆栈
- 必须记录完整堆栈到日志（`exc_info=exc`）
- 日志必须包含 `request_id`、`path`、`method`

## 2. 实现要求

### 2.1 所有 handler 必须从 request.state 获取 request_id

```python
request_id = getattr(request.state, "request_id", None)
```

### 2.2 所有 handler 必须传递 request_id 给 failure_response

```python
content=failure_response(code, message, details, request_id)
```

### 2.3 约束

- 不得修改已有错误码映射逻辑
- 不得修改已有 HTTP 状态码逻辑
- 不得在响应中暴露敏感信息
