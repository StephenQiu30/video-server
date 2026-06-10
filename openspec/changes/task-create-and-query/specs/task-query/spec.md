## ADDED Requirements

### Requirement: Task list returns user's tasks ordered by creation time
系统 SHALL 返回当前认证用户的所有任务，按 `created_at` 降序排列。

#### Scenario: List tasks for authenticated user
- **WHEN** 已认证用户发送 `GET /api/tasks`
- **THEN** 系统返回 HTTP 200，响应体为任务数组，按 `created_at` 降序排列，仅包含当前用户的任务

#### Scenario: Empty task list
- **WHEN** 已认证用户没有任何任务
- **THEN** 系统返回 HTTP 200，响应体为空数组

### Requirement: Task list supports state filter
系统 SHALL 支持按 `state` 查询参数过滤任务列表。

#### Scenario: Filter by valid state
- **WHEN** 已认证用户发送 `GET /api/tasks?state=queued`
- **THEN** 系统返回 HTTP 200，响应体仅包含 `state` 为 `queued` 的任务

#### Scenario: Invalid state filter rejected
- **WHEN** 已认证用户发送 `GET /api/tasks?state=not-exist`
- **THEN** 系统返回 HTTP 422，错误码为 `invalid_state`

### Requirement: Task list supports limit
系统 SHALL 支持 `limit` 查询参数限制返回数量。

#### Scenario: Limit results
- **WHEN** 已认证用户发送 `GET /api/tasks?limit=5`
- **THEN** 系统返回 HTTP 200，响应体最多包含 5 条任务

### Requirement: Task detail returns task basic information
系统 SHALL 返回指定任务的完整信息，包括 `id`、`source_url`、`title`、`state`、`progress`、`created_at`、`updated_at` 等字段。

#### Scenario: Get task detail for owner
- **WHEN** 已认证用户发送 `GET /api/tasks/{task_id}`，且该任务属于当前用户
- **THEN** 系统返回 HTTP 200，响应体包含任务的所有字段

#### Scenario: Task not found
- **WHEN** 已认证用户发送 `GET /api/tasks/{task_id}`，且该任务不存在
- **THEN** 系统返回 HTTP 404，错误码为 `not_found`

### Requirement: Task detail enforces ownership isolation
系统 SHALL 确保用户只能访问自己创建的任务。

#### Scenario: Cross-user access rejected
- **WHEN** 已认证用户 A 发送 `GET /api/tasks/{task_id}`，且该任务属于用户 B
- **THEN** 系统返回 HTTP 404，错误码为 `not_found`（不泄露任务存在性）

### Requirement: Task list annotates latest attempt
系统 SHALL 在任务列表和详情中标注该任务是否为最新尝试。

#### Scenario: Non-superseded task marked as latest
- **WHEN** 任务没有被后续重试任务替代
- **THEN** 响应中 `is_latest_attempt` 为 `true`

#### Scenario: Superseded task marked as not latest
- **WHEN** 任务已被后续重试任务替代
- **THEN** 响应中 `is_latest_attempt` 为 `false`

### Requirement: Task detail requires authentication
系统 SHALL 要求任务详情请求携带有效的 JWT 令牌。

#### Scenario: Unauthenticated detail request rejected
- **WHEN** 未认证用户发送 `GET /api/tasks/{task_id}`
- **THEN** 系统返回 HTTP 401

### Requirement: Task list reclaims stale active tasks
系统 SHALL 在查询时检查并回收超时的活跃任务。

#### Scenario: Stale active task marked as failed
- **WHEN** 存在运行超过最大时长限制的活跃任务
- **THEN** 系统将该任务状态更新为 `failed`，`failure_code` 为 `task_timeout`
