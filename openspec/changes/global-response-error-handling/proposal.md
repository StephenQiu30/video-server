## Why

video-server 后端已有初步的错误处理实现（`AppError`、`ErrorCode`、`failure_response`），但缺少统一的契约定义和 request id 集成。当前问题：

1. 错误响应格式虽已存在，但缺少明确的契约文档和 OpenSpec 规范。
2. Request ID 已在 middleware 中生成，但未包含在错误响应中，难以追踪。
3. 缺少契约测试覆盖所有错误路径。

需要通过 OpenSpec 将全局错误模型、exception handlers、request id 集成规范化，为后续 API 稳定性和可观测性提供基础。

## What Changes

- 新增 OpenSpec spec `global-error-model`：定义 failure envelope 契约、错误码分类、成功响应迁移原则
- 新增 OpenSpec spec `exception-handlers`：定义各类异常的处理方式和响应格式
- 新增 OpenSpec spec `request-id`：定义 request id 的生成、存储、传递和使用规范
- 修改 `apps/api/app/middleware/request_context.py`：将 request_id 存储到 request.state
- 修改 `apps/api/app/core/responses.py`：failure_response 函数增加 request_id 参数
- 修改 `apps/api/app/core/errors.py`：所有 exception handler 传递 request_id
- 新增 `apps/api/tests/test_error_contract.py`：契约测试覆盖所有错误路径

## Capabilities

### New Capabilities

- `global-error-model`: 全局错误模型规范，覆盖 failure envelope 结构、错误码分类、成功响应迁移原则
- `exception-handlers`: 异常处理器规范，覆盖 AppError、HTTPException、RequestValidationError、未知异常的处理方式
- `request-id`: Request ID 规范，覆盖生成、存储、传递、响应包含和日志记录

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- 受影响代码：`apps/api/app/middleware/request_context.py`、`apps/api/app/core/responses.py`、`apps/api/app/core/errors.py`
- 受影响测试：`apps/api/tests/test_error_contract.py`（新增）
- 受影响文档：`docs/prd/07-全局响应格式与异常处理.md`、`docs/plans/12-全局响应与异常处理计划.md`
