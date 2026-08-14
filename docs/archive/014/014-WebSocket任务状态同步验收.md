# 014 WebSocket 任务状态同步验收

- 状态：Accepted
- 日期：2026-08-10
- 结论：通过（Design → PRD → Plan → Acceptance 全链验收完成）
- 关联 Design：`docs/archive/014/014-WebSocket任务状态同步设计.md`
- 关联 PRD：`docs/archive/014/014-WebSocket任务状态同步需求.md`
- 关联 Plan：`docs/archive/014/014-WebSocket任务状态同步计划.md`

## 1. 冻结前置条件

- [x] 下载、分析、run、报告发布均产生单调 version、持久 task event 和对应 Outbox。
- [x] 测试环境至少可运行两个 Gateway 实例，并能控制 RabbitMQ 重复/乱序、网络中断、慢客户端和事件保留窗口。
- [x] 浏览器测试覆盖已登录 owner、另一用户、禁用账户、多个任务和多标签页。
- [x] 正常路径轮询请求数通过浏览器网络记录取证，不能只凭代码搜索判定。

## 2. 逐项验收

- [x] A1：连接建立收到 protocol v1 hello；正常执行期间下载与分析状态由 WebSocket 更新，网络记录中不存在固定周期高频 GET。
- [x] A2：缺失/过期 Cookie、禁用账户、错误 Origin/Host、生产非 TLS 和连接数超限均按稳定 close/error 行为拒绝。
- [x] A3：owner 可订阅自己的任务；跨用户与随机 UUID 订阅返回不泄露存在性的相同行为；角色/账户失效后已有连接关闭。
- [x] A4：重复、乱序、延迟和上一 run 的事件不能降低客户端最高 version 或覆盖当前 run/报告状态。
- [x] A5：相邻事件直接应用；版本跳跃暂停应用并 resync，不在缺口上继续猜测状态。
- [x] A6：断网、标签页休眠、网络切换与 Gateway 重启后，可按 after_version 有限重放或快照恢复到 PostgreSQL 最新事实。
- [x] A7：在恢复水位读取与实时接管之间注入事件，客户端最终恰好获得最新版本且无丢失窗口；多 Gateway 结果一致。
- [x] A8：慢消费者发送队列有界，中间进度可合并；终态、错误、取消和报告 available 不丢失，断开后可通过快照恢复。
- [x] A9：RabbitMQ/WebSocket 故障时页面显示降级状态并使用有退避低频 HTTP 查询；恢复后自动停止 fallback。
- [x] A10：同一 owner 的多个页面/任务复用单例连接；登出或切换用户会清空订阅/version，状态不会跨会话泄露。
- [x] A11：事件、连接 URL、日志和指标不包含 Cookie、JWT、owner hash、Prompt、报告正文、对象键、签名 URL 或完整任务 payload。
- [x] A12：1280px 与 390×844 下连接、重连、永久失败、手动刷新和 aria-live 状态可访问；键盘、200% 缩放和 reduced motion 可用。
- [x] A13：协议、认证、数据库事件、RabbitMQ、多实例、背压、前后端全量门禁与真实浏览器结果已记录并通过。

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

2026-08-10 已完成 protocol v1 真实链路：回放版本 10–19，并实时经历 queued、preparing、analyzing、validating、publishing、succeeded；终态后连续 16 秒无轮询 GET。恢复接管竞态、有界缓冲、重复/乱序/跳版、`resync.required`、慢消费者和低频 fallback 由服务端/前端自动化覆盖。

双 Gateway 实测中，两个独立 API 实例均收到 hello v1、从 PostgreSQL 回放 v1，并同时接收 RabbitMQ 实时 v2；禁用账户后两条既有连接均在复核周期内以 4401 关闭。单 owner 四连接上限、未登录、错误 Origin 均在真实握手中拒绝；Gateway Rabbit 临时队列权限经过完整应用启动验证。AuthProvider 登出/换用户会重置 socket、订阅和版本的组件测试通过。

刷新恢复、390×844 与 1280×900 无溢出、axe 0 violations；后端 446 tests、前端 101 tests、OpenAPI、镜像、schema 和 Compose 门禁全部通过。
