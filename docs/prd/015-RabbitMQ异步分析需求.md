# 015 RabbitMQ 异步分析与可靠投递需求

- 状态：Draft
- 日期：2026-08-10
- 关联 Design：`docs/design/015-RabbitMQ异步分析设计.md`

## 1. 用户价值

用户启动或重试 AI 视频分析后，API 应快速返回可查询任务，不因模型运行时间、Worker 重启或 RabbitMQ 暂时不可用而卡住请求。系统必须可靠地完成完整视频分析、报告发布和状态通知，并在重复投递、进程故障或基础设施恢复后保持同一任务事实。

## 2. 用户流程

1. 用户创建分析或对原任务发起重试，API 持久化任务、执行代次和发布意图后立即返回。
2. 宿主机 Analysis Worker 异步领取当前 run，校验并物化完整视频 artifact，再由受限 Agent 自主分析。
3. 技术性临时故障在同一 run 内按上限和退避恢复；页面持续展示排队、执行或等待重试状态。
4. 结构化结果校验通过后，独立 Report Publisher 生成并持久化报告，不再次调用 AI。
5. 失败、取消、Worker 重启或 broker 恢复后，系统从 PostgreSQL 和 Outbox 继续处理或给出稳定终态。

## 3. 产品规则

- 所有 AI 分析必须异步执行；HTTP 请求进程不得启动或等待 Codex/Claude CLI、FFmpeg 或报告渲染。
- PostgreSQL 是任务、run、报告和恢复状态的事实源；RabbitMQ 只传递命令和实时事件。
- 创建/重试事务必须同时写入任务事实、状态事件和唯一 Outbox 意图；RabbitMQ 不可用不破坏已提交任务。
- 消息只包含稳定 ID、run、版本和契约信息，不包含视频、预抽帧包、Prompt、结果正文、Secret 或签名 URL。
- Worker 必须读取并物化完整视频 artifact，由 Agent 自主观察视频；消息异步化不能退化为应用侧少量预抽帧分析。
- 每个 run 只有一个有效 lease owner，旧 run、重复消息和 fencing 失效 Worker 只能 no-op。
- 可重试业务故障使用数据库中的 attempt、`retry_wait` 和有界退避，不允许无限即时 requeue 热循环。
- 报告发布使用独立队列和无 OAuth Worker；报告失败只恢复发布阶段。
- 无效或超过投递上限的消息进入职责独立的 DLQ，人工审计后才能有界重放。
- RabbitMQ 或 Analysis Worker 降级时不得同步执行 AI；查询、取消和已发布报告下载仍应可用。

## 4. 产品验收标准（AC）

- AC-015-01：创建和手动重试在数据库事务成功后立即以 `201 Created`、`Location` 和任务状态投影返回，不等待 AI 或 broker confirm。
- AC-015-02：Analysis Worker 只从消息获得受限 ID，并从数据库读取、校验和物化完整视频 artifact。
- AC-015-03：数据库事实与 Outbox 原子提交；Publisher 仅在 mandatory publish 获得 broker confirm 后标记已发布。
- AC-015-04：重复、乱序、旧 run 和 lease 过期消息不会重复执行或覆盖当前结果。
- AC-015-05：技术重试在同一 run 内按退避与上限执行，不形成无限 requeue；手动重试才创建新 run。
- AC-015-06：结构化结果提交后由独立 Report Publisher 生成 Markdown/DOCX 并写 MinIO，不重复调用 AI。
- AC-015-07：无效消息和 poison message 进入对应 DLQ，回灌需要审计、新 event id 和次数上限。
- AC-015-08：RabbitMQ 丢失或重建后可从 PostgreSQL、Outbox、过期 lease 和待发布报告恢复。
- AC-015-09：取消、shutdown、超时和 lease 丢失可终止 CLI/FFmpeg 进程组并留下可恢复数据库状态。
- AC-015-10：消息、日志和指标不含视频内容、帧、Prompt、报告正文、Cookie、OAuth 或存储 Secret。
- AC-015-11：Publisher、Analysis Worker、Report Publisher 和 Gateway 使用按职责最小化的 RabbitMQ 权限。
- AC-015-12：队列积压、Outbox lag、confirm 失败、重试、lease、DLQ 和报告发布均有可观测指标与告警。

## 5. 非目标

首期不在消息中传输媒体或分析结果、不提供同步 AI fallback、不并行调用多个模型、不自动无限回灌 DLQ、不让 Analysis CLI 子进程访问 RabbitMQ/MinIO 凭据，也不把 broker 队列长度当作任务状态事实。
