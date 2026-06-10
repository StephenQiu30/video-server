## Context

异步下载主链路的第一步是把"接单"和"查单"稳定下来。当前实现已存在于 `apps/api/app/routers/tasks.py` 和 `apps/api/app/services/tasks.py`，包含完整的任务创建、列表查询、详情查询接口。本次变更的目标是将已有实现的行为契约通过 OpenSpec 规范化，并将 specs 推广到 `openspec/specs/` 作为当前事实层。

### 现有实现

- **路由层**：`apps/api/app/routers/tasks.py` — `POST /api/tasks`、`GET /api/tasks`、`GET /api/tasks/{task_id}`
- **服务层**：`apps/api/app/services/tasks.py` — 并发检查、事件记录、任务归属校验
- **模型层**：`apps/api/app/models.py` — `DownloadTask`、`TaskEvent` SQLAlchemy 模型
- **Schema 层**：`apps/api/app/schemas.py` — `TaskCreate`、`TaskRead` Pydantic 模型
- **共享层**：`packages/shared/video_downloader_shared/states.py` — `TaskState` 枚举

## Goals / Non-Goals

**Goals:**

- 规范化任务创建接口的请求/响应契约
- 规范化列表与详情查询的返回字段和过滤行为
- 定义状态初始化语义和入队行为
- 定义错误路径和边界条件

**Non-Goals:**

- 不涉及下载执行（Worker）逻辑
- 不涉及取消和重试接口规范（由后续 change 覆盖）
- 不涉及 SSE 流式推送规范
- 不涉及下载链接和 PDF 导出规范

## Decisions

### 1. 任务 ID 使用 UUID v4 字符串

**选择**：`DownloadTask.id` 为 `String(36)`，默认值 `uuid.uuid4()`。

**理由**：UUID 无需中心化发号器，适合分布式部署；字符串格式避免前端精度丢失。

### 2. 初始状态固定为 `queued`

**选择**：创建任务时 `state` 字段固定为 `TaskState.QUEUED.value`（"queued"），`progress` 固定为 0。

**理由**：任务创建后立即入队等待 Worker 拾取，`queued` 是最自然的初始状态。

### 3. 创建后立即入队

**选择**：`db.commit()` 后调用 `enqueue_download_task(task.id)` 将任务推入 Redis 队列。

**理由**：保证数据库记录先于队列入队，避免 Worker 拾取到不存在的任务。入队失败时将任务标记为 `failed` 并回滚。

### 4. 列表查询默认按创建时间倒序

**选择**：`GET /api/tasks` 按 `created_at DESC` 排序，支持 `state` 过滤和 `limit` 限制。

**理由**：用户最关心最新任务，倒序排列符合直觉。

### 5. 所有权隔离通过 `user_id` 过滤

**选择**：列表查询强制 `WHERE user_id = :current_user_id`，详情查询校验 `task.user_id == current_user.id`。

**理由**：多租户隔离，非 owner 访问返回 404 而非 403，避免泄露任务存在性。

## Risks / Trade-offs

- **风险**：如果接口先于状态模型定型，后续会频繁调整响应结构 → **缓解**：本次变更同时规范化状态模型和接口契约
- **风险**：SQLite 测试环境无法验证 PostgreSQL 特有的 migration → **缓解**：migration 逻辑仅在 PostgreSQL 上运行，测试使用 SQLite 跳过
