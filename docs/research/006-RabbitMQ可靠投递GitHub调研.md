# 006 RabbitMQ 可靠投递 GitHub 调研

- 日期：2026-08-11
- 目标：增强生产者、消费者、重试、死信和可观测性能力
- 结论：保留 aio-pika + Transactional Outbox，不引入 Celery；采用 RabbitMQ 官方策略与成熟项目的可配置连接/QoS 模式

## 1. 对照结果

| 来源 | 成熟做法 | 本系统采用方式 |
| --- | --- | --- |
| [RabbitMQ reliability guide](https://www.rabbitmq.com/docs/reliability) | publisher confirm、consumer manual ack 共同形成至少一次投递 | 已有 mandatory persistent confirm 与 ACK-after-commit，继续保留 |
| [RabbitMQ DLX guide](https://www.rabbitmq.com/docs/4.1/dlx) | DLX、TTL、容量应使用 policy，避免不可在线修改的 `x-arguments` | 新队列只固定 `x-queue-type`；DLX/TTL/容量/overflow 改由 policy 管理 |
| [RabbitMQ quorum queues](https://www.rabbitmq.com/docs/4.2/quorum-queues) | 关键长生命周期队列使用 quorum、confirm、manual ack、delivery limit；可启用 at-least-once dead-lettering | 生产示例使用 quorum；配置 `delivery-limit=5`、`overflow=reject-publish`、`dead-letter-strategy=at-least-once` |
| [rabbitmq-server 配置样例](https://github.com/rabbitmq/rabbitmq-server/blob/main/deps/rabbit/docs/rabbitmq.conf.example) | 心跳、消息上限、consumer timeout 与队列限制显式配置 | 心跳 60 秒、ACK deadline 1 小时、消息上限 1 MiB |
| [rabbitmq-server Prometheus 指标定义](https://github.com/rabbitmq/rabbitmq-server/blob/main/deps/rabbitmq_prometheus/metrics.md) | 监控 unroutable、delivery-limit、ready/unacked、consumer 数量 | 增加无消费者、容量逼近、长期 unacked、投递上限和不可路由告警 |
| [aio-pika RobustConnection](https://github.com/mosquito/aio-pika/blob/master/aio_pika/robust_connection.py) | robust channel 自动恢复，重连间隔与 connection name 可配置 | 所有 producer/consumer 统一 heartbeat、reconnect interval、timeout 和连接名 |
| [OpenStack oslo.messaging RabbitMQ driver](https://github.com/openstack/oslo.messaging/blob/master/oslo_messaging/_drivers/impl_rabbit.py) | 独立配置 heartbeat、重连退避、prefetch 与 quorum | 采用显式连接参数和有界 prefetch；不引入其 RPC 抽象 |
| [Celery configuration](https://github.com/celery/celery/blob/main/docs/userguide/configuration.rst) | 长任务 prefetch=1；quorum 必须配 confirm；重连后防止过量预取 | AI Worker 继续 prefetch=1，下载并发与线程数一致，发布始终 confirm |

## 2. 未采用方案

- 不引入 Celery/Kombu：现有 Outbox、job/run 状态机、lease 和幂等 claim 已覆盖任务事实，引入框架会形成第二套重试语义。
- 不使用无限 `nack(requeue=true)`：热循环无法退避且会阻塞队列；下载消息现在最多 broker 重投一次，之后进入 DLQ，数据库 queued recovery 生成新事件恢复。
- 不自动回灌 DLQ：回灌需要操作者、原因、新 event ID、次数上限和数据库审计。
- 不自动删除非空旧队列：从硬编码参数迁移到 policy 只允许对空闲且空的主队列执行显式安全重建。
- 不让 DLQ 无限增长：按条数和字节双重限制，并在任何死信出现时告警；不配置自动 TTL，保留人工调查窗口。

## 3. 参数基线

| 参数 | 开发默认值 | 生产建议 |
| --- | ---: | ---: |
| queue type | classic | quorum（至少三节点才具备节点级高可用） |
| message TTL | 24 小时 | 不短于输入 artifact 的可分析窗口 |
| main queue | 10,000 条 / 256 MiB | 按峰值与处置时长调整 |
| delivery limit | 5 | 3–10，领域重试仍由数据库 attempt 控制 |
| DLQ | 10,000 条 / 256 MiB | 配合告警与人工处置，不自动无限回灌 |
| heartbeat / reconnect | 60 秒 / 5 秒 | 按跨区网络 RTT 调整，heartbeat 不低于 10 秒 |
| consumer ACK deadline | 1 小时 | 必须高于最长一次视频分析执行时间 |
