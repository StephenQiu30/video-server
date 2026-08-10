# 015 RabbitMQ 异步分析与可靠投递验收

- 状态：Pending
- 日期：2026-08-10
- 结论：Pending
- 关联 Design：`docs/design/015-RabbitMQ异步分析设计.md`
- 关联 PRD：`docs/prd/015-RabbitMQ异步分析需求.md`
- 关联 Plan：`docs/plans/015-RabbitMQ异步分析计划.md`

## 1. 冻结前置条件

- [ ] 使用项目有权处理的受控完整视频，并准备可成功、可重试失败、不可重试失败和取消场景。
- [ ] RabbitMQ 启用独立 vhost/账号、publisher confirm、三类 routing key、durable queue 与各自 DLQ。
- [ ] 可在 Outbox、publish、claim、AI、数据库提交、报告上传和 ACK 的关键点注入故障。
- [ ] 013 run/version、012 report 和 014 task event 契约已冻结并由同一当前态 schema 提供。

## 2. 逐项验收

- [ ] A1：创建与手动重试在 job/run/event/Outbox 事务提交后立即返回 `201 Created`、Location 和状态投影；RabbitMQ 关闭时也不等待 AI 或 broker。
- [ ] A2：Outbox Publisher 使用 persistent mandatory publish，只有 confirm ACK 后标记 published；NACK、unroutable、超时和断连保留可重投事实。
- [ ] A3：`analysis.requested` 消息只含 schema/event/job/run/version 等白名单字段；Worker 从 PostgreSQL 读取并校验完整 artifact，消息不含视频或预抽帧包。
- [ ] A4：Agent 工作区实际物化完整视频并自主取证；分析结果仍满足 010 的连续分镜、高光和资产证据校验。
- [ ] A5：重复、乱序、上一 run、旧 expected version 和过期 lease 消息只产生 ACK no-op，不能重复运行或覆盖当前事实。
- [ ] A6：限流、临时 CLI 失败、超时和非法模型输出在同一 run 内按 retry_wait/attempt 上限恢复，不发生无限 `nack(requeue=true)` 热循环。
- [ ] A7：手动重试创建同一 job 的新 run 和新 event；系统技术重试不增加 run_no，两种次数在 API/UI 中准确区分。
- [ ] A8：AI 提交 validated result 后由独立 Report Publisher 生成 Markdown/DOCX 并上传 MinIO；报告阶段故障恢复不再次调用 AI。
- [ ] A9：未知 schema、缺字段、超限和 poison message 进入职责对应 DLQ；回灌有审计、新 event id 和次数上限，不自动无限循环。
- [ ] A10：broker 丢失/重建后，可从未发布 Outbox、queued、retry_wait、过期 lease 与 validated/publish_failed 状态恢复，最终结果唯一。
- [ ] A11：取消、Worker shutdown、超时和 lease 丢失终止 CLI→shell→FFmpeg 整个进程组，数据库留下可恢复或明确终态且无孤儿进程。
- [ ] A12：Publisher、Analysis Worker、Report Publisher、Gateway 权限互相隔离；越权 publish/consume 和 CLI 子进程读取凭据全部失败。
- [ ] A13：消息、DLQ、日志和指标不含视频/帧、原始 URL、owner hash、Prompt、结果/报告正文、Cookie、OAuth 或存储 Secret。
- [ ] A14：ready/unacked/dead、最老消息、Outbox lag、confirm、claim no-op、retry、lease 和报告积压指标与告警可触发且 label 保持低基数。
- [ ] A15：完整 API → Outbox → RabbitMQ → Host Worker → report queue → MinIO → API/UI E2E、全量工程门禁和 Compose 解析已记录并通过。

## 3. 建议验收命令

后端（在 `backend/` 执行）：

```bash
uv sync --frozen --dev
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest
```

前端（在 `frontend/` 执行）：

```bash
npm ci
npm run openapi:check
npm run lint
npm run format:check
npm test
npm run build
```

根目录配置解析：

```bash
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
```

## 4. 验收证据

待实际执行后记录提交哈希、job/run/event/report ID、消息 envelope、confirm 与 delivery 次数、lease owner、故障注入时间线、DLQ/回灌审计、进程树检查、对象哈希、指标截图和全部命令退出码。未完成真实 broker 故障恢复与完整视频队列级 E2E 前不得标记 Passed。
