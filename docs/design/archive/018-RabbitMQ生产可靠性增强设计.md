# 018 RabbitMQ 生产可靠性增强设计

- 状态：Accepted
- 日期：2026-08-11
- 关联 PRD：`docs/prd/archive/018-RabbitMQ生产可靠性增强需求.md`
- 关联 Plan：`docs/plans/archive/018-RabbitMQ生产可靠性增强计划.md`
- 关联 Acceptance：`docs/acceptance/archive/018-RabbitMQ生产可靠性增强验收.md`
- 关联设计：`docs/design/archive/015-RabbitMQ异步分析设计.md`
- 调研：`docs/research/006-RabbitMQ可靠投递GitHub调研.md`

## 1. 目标与不变量

本设计增强既有 `PostgreSQL Outbox → RabbitMQ → Worker → PostgreSQL` 链路，不改变 PostgreSQL 是任务事实源的约束。

- Producer 只有收到 mandatory publish 的 broker confirm ACK 后才能确认 Outbox 已发布。
- Consumer 只有在数据库事实提交后 ACK；重复投递由 job/run/version/lease 幂等收敛。
- RabbitMQ 投递次数只防止 poison message，不替代领域 `attempt/retry_wait`。
- DLQ 不自动回灌；重放必须可审计、有新 event ID、有次数上限。
- 消息只包含 ID、版本和有界元数据，不携带视频、URL、Prompt、报告正文或 Secret。

## 2. Broker 拓扑与策略

`video.events` 和 `video.events.dead` 保持 durable。三条主队列和三条 DLQ 按职责隔离。

可变能力使用 RabbitMQ policy：

- 主队列：DLX、dead routing key、message TTL、max length、max bytes、overflow。
- quorum 主队列：额外启用 `delivery-limit` 与 `dead-letter-strategy=at-least-once`。
- DLQ：条数和字节双重上限，`drop-head` 保留最新故障；任何非空状态必须告警。
- 只有不可在线改变的 queue type 使用 `x-queue-type`。

主队列达到容量时使用 `reject-publish`，由 publisher confirm NACK 使 Outbox 保留并退避重发，避免静默删除最老命令。

## 3. Producer

- 使用 persistent message、message ID、correlation ID、schema header。
- 使用 robust connection、publisher confirms、`mandatory=true`、`on_return_raises=true`。
- 连接超时、publish 超时、heartbeat、reconnect interval 全部由环境配置。
- 不以 confirm 表示业务消费完成；confirm 只表示 broker/目标队列已经承担消息责任。

## 4. Consumer

- Download Worker 的 prefetch 与执行线程数一致；Analysis Worker 固定为 1；Report Worker 独立配置。
- 所有 consumer 使用 manual ACK 和 robust connection。
- 非法契约立即 `nack(requeue=false)` 进入职责 DLQ。
- 基础设施异常最多原消息重投一次；再次失败进入 DLQ，避免热循环。
- Download/Analysis queued recovery 按稳定 job/version 重新写 Outbox，新事件恢复投递但不创建新任务。
- broker `consumer_timeout=1h` 高于最长单次分析窗口，防止无限 unacked 占用日志和磁盘。

## 5. Classic 与 Quorum

- 开发环境默认 classic，降低本地资源占用。
- 生产示例默认 quorum；publisher confirm 是强制条件。
- 单节点 quorum 只有一致写入语义，不提供节点故障高可用；正式 HA 需要奇数节点集群，通常为三节点。
- queue type 不能在线修改。旧硬编码队列默认保留；仅在明确设置迁移开关且队列为空、无消费者时安全删除并重建主队列。

## 6. DLQ 处置

1. 查看 queue、routing key、`x-death` reason/count、event/job ID，不输出消息中的敏感内容。
2. 对照数据库判断任务是否已终态；终态消息不重放。
3. 修复根因后使用 DLQ CLI，填写 actor/reason。
4. 服务生成新 event ID，保留 original event ID 和 replay count；broker confirm 后才 ACK 原死信。
5. 单个原事件最多重放三次；失败保留原消息。

## 7. 可观测性

除已有 ready/unacked/dead、Outbox lag 与 confirm 计数外，增加：

- 有 backlog 但 consumer 为 0；
- 主队列超过容量基线 80%；
- delivery 超过 45 分钟仍未 ACK；
- delivery-limit 触发；
- mandatory publish 被返回为不可路由。

## 8. 验收标准

- policy 可调整 DLX、TTL、条数和字节限制，无需应用重新部署或删除新式队列。
- classic/quorum 新建拓扑均可初始化，quorum 显示 at-least-once dead-letter policy。
- 所有生产者和消费者使用显式 heartbeat/reconnect/timeout。
- 下载消费者第二次基础设施失败进入 DLQ，queued job 能在同任务身份上重新发布。
- Outbox confirm、非法消息、重复消息、DLQ 审计重放、Compose 解析和 RabbitMQ 实例初始化测试通过。
