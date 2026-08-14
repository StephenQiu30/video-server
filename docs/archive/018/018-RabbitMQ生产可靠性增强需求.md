# 018 RabbitMQ 生产可靠性增强需求

- 状态：Accepted
- 日期：2026-08-11
- 关联 Design：`docs/archive/018/018-RabbitMQ生产可靠性增强设计.md`
- 关联 Plan：`docs/archive/018/018-RabbitMQ生产可靠性增强计划.md`
- 关联 Acceptance：`docs/archive/018/018-RabbitMQ生产可靠性增强验收.md`

## 1. 目标

在不改变 PostgreSQL 任务事实源的前提下，保证 Outbox 发布、RabbitMQ 承载、Worker 消费和 DLQ 处置具备有界重试、可恢复性和可审计证据。

## 2. 功能需求

- FR-018-01：Producer 使用 persistent message、mandatory publish 和 broker confirm；NACK 或不可路由时保留 Outbox。
- FR-018-02：Consumer 仅在数据库事实提交后 ACK，非法契约进入职责 DLQ，基础设施失败不得形成热循环。
- FR-018-03：主队列和 DLQ 具备 TTL、条数、字节、overflow 与 dead-letter policy；生产示例支持 quorum。
- FR-018-04：queued recovery 复用稳定任务身份重新写 Outbox，不创建重复业务任务。
- FR-018-05：DLQ 重放记录 actor、reason、original event ID 和 replay count，并限制最多三次。
- FR-018-06：暴露 backlog、consumer、delivery、confirm、DLQ 和不可路由消息的低基数指标或告警依据。

## 3. 安全与可靠性

消息只携带 ID、版本和有界元数据；不得包含 URL、Secret、Prompt、报告正文或媒体。开发 classic 与生产 quorum 的差异必须显式配置，队列类型迁移只能在空队列、无消费者和明确授权下执行。

## 4. 成功标准

拓扑策略、confirm、ACK/NACK、重复投递、恢复、DLQ 审计重放、Compose 配置和实例初始化均有自动化或真实环境证据。
