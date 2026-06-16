## 1. OpenSpec Change Artifacts

- [x] 1.1 创建 `openspec/changes/task-create-and-query/proposal.md`
- [x] 1.2 创建 `openspec/changes/task-create-and-query/design.md`
- [x] 1.3 创建 `openspec/changes/task-create-and-query/specs/task-create/spec.md`
- [x] 1.4 创建 `openspec/changes/task-create-and-query/specs/task-query/spec.md`
- [x] 1.5 创建 `openspec/changes/task-create-and-query/tasks.md`

## 2. 推广 Specs 到 Baseline

- [x] 2.1 推广 `task-create` spec 到 `openspec/specs/task-create/spec.md`
- [x] 2.2 推广 `task-query` spec 到 `openspec/specs/task-query/spec.md`

## 3. 验证

- [x] 3.1 验证 `POST /api/tasks` 返回 HTTP 201、任务 ID 和 `queued` 状态
- [x] 3.2 验证 `GET /api/tasks` 返回当前用户的任务列表，按 `created_at` 降序
- [x] 3.3 验证 `GET /api/tasks/{task_id}` 返回任务详情
- [x] 3.4 验证未认证请求返回 401
- [x] 3.5 验证跨用户访问返回 404
- [x] 3.6 运行 `npm test` 确认全部 166 个测试通过

## 4. 文档更新

- [x] 4.1 更新 `docs/plans/04-创建任务与状态查询计划.md` 状态从 `draft` 到 `accepted`
