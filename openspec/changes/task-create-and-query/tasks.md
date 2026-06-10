## 1. 验证现有实现

- [ ] 1.1 验证 `POST /api/tasks` 返回 HTTP 201、任务 ID 和 `queued` 状态（已有测试 `test_task_api_flow_coverage_taskread_fields_and_cancel_retry`）
- [ ] 1.2 验证 `GET /api/tasks` 返回当前用户的任务列表，按 `created_at` 降序（已有测试覆盖）
- [ ] 1.3 验证 `GET /api/tasks/{task_id}` 返回任务详情（已有测试覆盖）
- [ ] 1.4 验证未认证请求返回 401（已有测试 `test_create_task_requires_auth`）
- [ ] 1.5 验证跨用户访问返回 404（已有测试 `test_task_endpoints_cross_user_boundary_and_download_link_expired_or_miss`）
- [ ] 1.6 验证速率限制、每日配额、并发限制（已有测试覆盖）
- [ ] 1.7 运行 `npm test` 确认全部 160 个测试通过

## 2. 文档更新

- [ ] 2.1 更新 `docs/plans/04-创建任务与状态查询计划.md` 状态从 `draft` 到 `accepted`
- [ ] 2.2 确认 OpenSpec change 四个 artifact（proposal、design、specs、tasks）已创建完成
