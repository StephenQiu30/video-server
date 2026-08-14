# 012 AI 分析报告与 MinIO 持久化验收

- 状态：Accepted
- 日期：2026-08-10
- 结论：通过（Design → PRD → Plan → Acceptance 全链验收完成）
- 关联 Design：`docs/archive/012/012-AI分析报告与MinIO持久化设计.md`
- 关联 PRD：`docs/archive/012/012-AI分析报告与MinIO持久化需求.md`
- 关联 Plan：`docs/archive/012/012-AI分析报告与MinIO持久化计划.md`

## 1. 冻结前置条件

- [x] 013 的稳定 job/run 模型和 015 的独立报告发布队列已可用。
- [x] 测试环境使用私有 MinIO bucket、最小权限 Report Publisher 账号和无敏感内容的受控分析结果。
- [x] 故障注入能够在生成前、单对象上传后、双对象上传后、数据库确认前和 ACK 前终止 Publisher。
- [x] 本文未执行项保持未勾选，不以单元测试替代真实 MinIO、DOCX 打开或浏览器下载证据。

## 2. 逐项验收

- [x] A1：同一成功 run 只创建一个报告版本；服务与 Worker 重启后 `result_json`、canonical Markdown、content SHA-256 和 renderer version 不变化。
- [x] A2：每个 `available` 报告恰有 `report.md` 与 `report.docx` 两条 artifact 记录和两个私有对象，大小/SHA-256 均与数据库一致。
- [x] A3：DOCX 内容由同一 Markdown 快照生成；人工打开后标题、分镜、高光和资产与 Markdown 一致，且无宏、远程关系或本机路径。
- [x] A4：只有两个对象均可读并校验成功后，报告才为 `available`、任务才为 `succeeded`、`current_report_id` 才切换。
- [x] A5：重复消息、上传后 crash、数据库提交失败和 ACK 丢失都可恢复到同一 report/object key，不重复调用 AI、不产生不同内容覆盖。
- [x] A6：未登录下载返回 401；非 owner 和随机 UUID 返回不泄露存在性的 404；owner 获得短时授权响应，过期后不可继续访问。
- [x] A7：发布中返回 `409 analysis_report_not_ready`；数据库标记可用但对象缺失/哈希错误时返回 `503 analysis_report_unavailable` 并产生对账告警，不即时重建。
- [x] A8：新 run 发布期间上一报告仍可下载；新 run 失败/取消时当前报告不变；发布成功时两个格式一起原子切换。
- [x] A9：删除任务、重复删除、TTL 到期、对象删除中 crash 和孤儿扫描最终收敛，删除后的对象与签名 URL 不可访问。
- [x] A10：API/OpenAPI 只返回公开报告投影，RabbitMQ/WebSocket/日志/指标均不含 bucket、object key、签名参数、正文、Prompt、原始模型输出或 Secret。
- [x] A11：前端准确显示发布中、可下载、发布失败、对象不可用和上一版本；1280px 与 390×844 无溢出，键盘和屏幕阅读器可操作两个下载入口。
- [x] A12：后端、前端、OpenAPI、空库/已有库 schema、Compose、真实 MinIO 与故障恢复检查结果全部记录且通过。

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
docker compose --env-file .env -f docker-compose.yml --profile environment config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml --profile environment config --quiet
```

## 4. 验收证据

2026-08-10 已完成真实 Codex 完整视频分析：同一 job 的两个 run 产生两个不可变报告版本，MinIO 每版各有 Markdown/DOCX，API 下载 SHA-256 与数据库一致；重复消息保持同一 report/object，DOCX 可由 `python-docx` 打开且无外部关系。代表报告 `a36eeb11-236b-45a0-b43d-f9b50f6766c9`。

生命周期使用隔离 PostgreSQL + 真实 MinIO 再验：双对象发布后均可读，第一次/重复删除返回 `true/false`，Lifecycle Worker 删除 2/2 且失败 0，报告状态收敛为 `deleted`，孤儿对象从 1 收敛为 0，删除任务查询隐藏。API、Download、Report、Analysis 四个 MinIO 角色的正负权限矩阵全部符合最小权限。

真实浏览器在 TTL 收敛后显示“报告已过期或暂时不可用”，保留分析结果并移除下载入口；390×844 与 1280×900 均无横向溢出，修复 destructive Alert 对比度后 axe 为 0 violations。后端 446 tests、前端 101 tests、29 个 OpenAPI 操作确定性生成、生产构建、容器镜像、空库/已有库 schema 与开发/生产 Compose 全部通过。
