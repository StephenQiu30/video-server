# Task Create

## Purpose

定义任务创建接口的请求/响应契约、状态初始化语义、入队行为和错误路径。

## ADDED Requirements

### Requirement: Task creation returns task ID and queued status
系统 SHALL 接受已认证用户的任务创建请求，返回 HTTP 201 状态码，响应体包含任务 ID 和 `state` 字段值为 `queued`。

#### Scenario: Successful task creation with valid URL
- **WHEN** 已认证用户提交 `POST /api/tasks`，请求体包含合法且平台支持的 `url`
- **THEN** 系统返回 HTTP 201，响应体包含 `id`（UUID 字符串）、`state` 为 `queued`、`progress` 为 0、`attempt_no` 为 1

#### Scenario: Task creation with optional metadata
- **WHEN** 已认证用户提交 `POST /api/tasks`，请求体包含 `url`、`title`、`cover_url`、`duration_seconds`、`format_id`、`format_label`
- **THEN** 系统返回 HTTP 201，响应体包含所有提交的可选字段

### Requirement: Task creation enqueues to worker queue
系统 SHALL 在任务记录写入数据库后，将任务 ID 推入 Redis 队列供 Worker 拾取。

#### Scenario: Successful enqueue after database commit
- **WHEN** 任务记录成功写入数据库
- **THEN** 系统调用 `enqueue_download_task(task_id)` 将任务推入队列

#### Scenario: Enqueue failure marks task as failed
- **WHEN** 任务记录写入数据库后，入队操作失败
- **THEN** 系统将任务状态更新为 `failed`，`failure_code` 为 `queue_unavailable`，并抛出错误

### Requirement: Task creation records initial event
系统 SHALL 在任务创建时记录一条 `TaskEvent`，状态为 `queued`。

#### Scenario: Initial event recorded
- **WHEN** 任务成功创建并提交
- **THEN** `task_events` 表中存在一条记录，`task_id` 等于新任务 ID，`state` 为 `queued`

### Requirement: Task creation requires authentication
系统 SHALL 要求任务创建请求携带有效的 JWT 令牌。

#### Scenario: Unauthenticated request rejected
- **WHEN** 未认证用户提交 `POST /api/tasks`
- **THEN** 系统返回 HTTP 401

### Requirement: Task creation validates URL platform support
系统 SHALL 在创建任务前验证 URL 所属平台是否受支持。

#### Scenario: Unsupported platform URL rejected
- **WHEN** 已认证用户提交 `POST /api/tasks`，请求体包含不支持平台的 URL
- **THEN** 系统返回 HTTP 422，错误码为 `invalid_url`

### Requirement: Task creation enforces rate limiting
系统 SHALL 对任务创建请求实施速率限制。

#### Scenario: Rate limit exceeded
- **WHEN** 已认证用户在速率限制窗口内发送超过限额的任务创建请求
- **THEN** 系统返回 HTTP 429，错误码为 `rate_limited`

### Requirement: Task creation enforces daily quota
系统 SHALL 检查用户的每日任务配额。

#### Scenario: Daily quota exceeded
- **WHEN** 已认证用户当日已创建的任务数达到 `daily_task_quota` 上限
- **THEN** 系统返回 HTTP 429，错误码为 `limit_exceeded`

### Requirement: Task creation enforces concurrency limit
系统 SHALL 检查用户的并发任务数限制。

#### Scenario: Concurrency limit exceeded
- **WHEN** 已认证用户当前有活跃任务数达到 `concurrent_task_quota` 上限
- **THEN** 系统返回 HTTP 429，错误码为 `limit_exceeded`
