# 015 RabbitMQ 异步分析与可靠投递计划

- 状态：Ready
- 日期：2026-08-10
- 关联 Design：`docs/design/015-RabbitMQ异步分析设计.md`
- 关联 PRD：`docs/prd/015-RabbitMQ异步分析需求.md`
- 依赖：013 run/version 模型；012 报告发布状态；014 公开实时事件契约

## 1. 实施顺序

1. 盘点并冻结现有 `video.events`、`video.analysis`、Outbox 和 Worker 基线，定义三类 routing key、envelope v1、队列参数、DLX/DLQ 与最小权限矩阵。
2. 让创建与 013 重试事务统一写 job/run/task event/Outbox，响应固定为 `201 Created + Location + 状态投影`，不等待 RabbitMQ。
3. 重构 Outbox Publisher：批量 claim、persistent/mandatory publish、publisher confirm 后标记、连接退避和不确定 confirm 重投。
4. 改造 Analysis Worker envelope 与 claim，显式校验 run、expected version、lease fencing 和完整 artifact，再物化到 run/attempt 隔离目录。
5. 将可重试业务错误收敛到数据库 `retry_wait/retry_at/attempt`，由 Recovery Sweeper 生成新 Outbox；移除无限 immediate requeue。
6. 接入 012 的独立 `video.analysis-report` 队列和 Report Publisher，AI Worker 只提交已校验结果与发布意图。
7. 接入 014 的 `task.state.changed`，每个状态事务产生受限公开投影；Gateway 只消费自己独占的实时队列。
8. 为每个 durable queue 配置独立 DLQ、poison 上限、告警和人工有界重放工具；实现 broker/lease/Outbox 恢复扫描。
9. 完成权限、消息、重复投递、故障注入、完整视频 Agent、报告发布和取消进程树 E2E，回填 Acceptance。

## 2. DAC/AC 映射

| 契约 | 实现 | 验证 |
| --- | --- | --- |
| DAC-015-01 / AC-015-01 | job/run/event/Outbox 事务与异步 201 响应 | RabbitMQ 关闭下 API 延迟和持久事实测试 |
| DAC-015-02 / AC-015-02 | ID-only envelope、完整 artifact 物化 | 消息白名单、哈希/大小、Agent 工作区 E2E |
| DAC-015-03 / AC-015-03 | transactional Outbox + mandatory confirm | rollback、unroutable、ACK/NACK/断连测试 |
| DAC-015-04 / AC-015-04 | run/version/lease fencing 与幂等 claim | 重复、乱序、旧 run、lease 过期测试 |
| DAC-015-05/06 / AC-015-05 | run 内退避 attempt 与手动新 run | retry_wait、Sweeper、并发手动重试测试 |
| DAC-015-07 / AC-015-06 | 独立报告队列与无 OAuth Publisher | AI 提交后 crash、报告重试、调用计数测试 |
| DAC-015-08 / AC-015-07 | 独立 DLQ 与审计回灌 | poison、未知版本、delivery 上限和 replay 测试 |
| DAC-015-09 / AC-015-08 | DB/Outbox/lease/report 恢复扫描 | broker 丢失、队列重建和幂等恢复演练 |
| DAC-015-10 / AC-015-09 | shutdown/cancel/timeout 进程组监管 | CLI→shell→FFmpeg 真实进程树测试 |
| DAC-015-11 / AC-015-10/11 | 消息白名单与 RabbitMQ ACL | 权限负向测试、Secret/日志扫描 |
| DAC-015-12 / AC-015-12 | 指标、告警和全链 E2E | backlog/confirm/DLQ/lease 仪表与 Acceptance |

## 3. 队列与消费者测试

- Topology：durable exchange/queue、routing key、DLX、TTL、最大长度和参数冲突 fail-fast。
- Publisher：事务回滚不发布、mandatory unroutable、confirm ACK/NACK/超时、连接断开和重复发布。
- Consumer：严格 schema、未知版本、重复 event、active run/fencing、ACK 前数据库提交和 ACK 失败重投。
- Retry：Provider 临时故障、超时、非法输出、数据库暂时不可用、process shutdown 和 poison message 分类。
- Recovery：Outbox backlog、queued、retry_wait、过期 lease、validated/publish_failed 可重建命令且不会重复执行业务。
- Shutdown：先停止取新消息，取消进程树，提交可恢复状态，再关闭 channel；验证无孤儿进程和未清理 lease。

## 4. 安全与运行验证

- RabbitMQ 用户分别限制 Publisher publish、Analysis consume、Report consume 和 Gateway consume 权限；Analysis CLI 子进程无 broker/数据库/MinIO 凭据。
- envelope、header、日志和 DLQ 检查不出现视频/帧、原始 URL、owner hash、Prompt、结果/报告正文、Cookie 或 Secret。
- Analysis Worker 保持宿主机 OAuth 单并发或受控 prefetch；Report Publisher 无个人 OAuth，可独立扩容但受数据库/MinIO 上限。
- readiness 分别报告数据库、Outbox、RabbitMQ 和 Worker 能力；故障时不启动同步 AI fallback。

## 5. 端到端与发布顺序

1. 用现有受控短视频执行 API → Outbox → RabbitMQ → Host Worker → validated result → report queue → MinIO → API/UI 全链。
2. 在 publish 前、claim 后、AI 完成前、结果提交后、对象上传后和 ACK 前分别终止进程，确认恢复结果唯一。
3. 先部署兼容新 envelope 的消费者和 topology，再启用生产者；不兼容契约以 schema version 同发布切换。
4. 发布异常时暂停 Publisher/Consumer 并保留数据库事实；不得清空队列、无限 requeue 或改走同步执行。

## 6. 不做项

不新建第二个通用 exchange、不在消息中放媒体/Prompt/结果、不使用 RabbitMQ 作为历史事实、不自动无限回灌 DLQ、不容器化复制个人 OAuth，也不维持旧消息双写兼容层。
