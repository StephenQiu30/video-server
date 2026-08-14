# 018 RabbitMQ 生产可靠性增强计划

- 状态：Completed
- 日期：2026-08-11
- 关联 Design：`docs/design/archive/018-RabbitMQ生产可靠性增强设计.md`
- 关联 PRD：`docs/prd/archive/018-RabbitMQ生产可靠性增强需求.md`
- 完成证据：`docs/acceptance/archive/018-RabbitMQ生产可靠性增强验收.md`

## 实施顺序

1. 把可变队列能力迁移到 RabbitMQ policy，并保留 queue type 的显式配置。
2. 为 Producer 增加 robust connection、mandatory publish、confirm 和稳定 event ID。
3. 收敛 Download/Analysis/Report consumer 的 prefetch、ACK/NACK 和基础设施失败预算。
4. 实现 queued recovery、职责 DLQ、审计重放和重放上限。
5. 增加拓扑、消息、Outbox、Consumer、DLQ、指标和 Compose 契约测试。

## 完成说明

计划范围已由提交 `a047b89` 落地；2026-08-14 当前代码定向回归继续通过。RabbitMQ 集群级高可用部署属于环境容量规划，不是本计划的代码遗留项。
