## Why

异步下载主链路需要先将"接单"和"查单"稳定下来，让 API 与 Worker 解耦。当前实现已存在但缺少规范层定义，需要通过 OpenSpec 将任务创建、列表查询和详情查询的行为契约规范化，为后续 Worker 执行、取消重试等能力提供稳定基础。

## What Changes

- 新增 OpenSpec 规范：定义任务创建接口的请求/响应契约、状态初始化语义
- 新增 OpenSpec 规范：定义任务列表和详情查询的返回字段与过滤行为
- 更新 PLAN04 文档状态从 `draft` 到 `accepted`

## Capabilities

### New Capabilities

- `task-create`: 任务创建接口规范，覆盖请求 schema、响应 schema、初始状态语义、入队行为、错误路径
- `task-query`: 任务列表与详情查询规范，覆盖返回字段、状态过滤、所有权隔离、过期清理行为

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- 受影响代码：`apps/api/app/routers/tasks.py`、`apps/api/app/services/tasks.py`、`apps/api/app/schemas.py`、`apps/api/app/models.py`
- 受影响测试：`apps/api/tests/test_task_endpoints.py`
- 受影响文档：`docs/plans/04-创建任务与状态查询计划.md`
