# 014 WebSocket 任务状态同步计划

- 状态：Completed
- 日期：2026-08-10
- 关联 Design：`docs/design/014-WebSocket任务状态同步设计.md`
- 关联 PRD：`docs/prd/014-WebSocket任务状态同步需求.md`
- 依赖：013 任务版本/run 投影；015 `task.state.changed` 事件
- 完成证据：`docs/acceptance/014-WebSocket任务状态同步验收.md`

## 1. 实施顺序

1. 冻结协议版本、hello/subscribe/resync/event schema、close code、错误白名单、心跳和资源上限。
2. 在当前态 SQL、ORM 和 repository 中增加任务单调 `version` 与 `task_events`，让下载、分析、重试、取消和报告发布事务同时写事件与 Outbox。
3. 实现任务事件查询：按 owner/task/version 授权读取、有限重放、当前快照和保留窗口降级。
4. 实现 WebSocket Gateway：同源 Cookie 认证、Origin/Host/TLS 校验、订阅 owner 授权、账户状态复核和连接限额。
5. 绑定每 Gateway 独占自动删除 RabbitMQ 队列，建立按 owner/task 的连接索引、有界发送队列和终态优先策略。
6. 实现“数据库水位 → 连接缓冲 → 有限重放/快照 → 排空缓冲 → 实时”恢复流程与版本缺口 resync。
7. 在前端实现按 owner 会话隔离的单例连接管理器、订阅注册、版本 reducer、抖动退避、连接状态和低频 HTTP 降级。
8. 将下载与分析 hooks 从固定轮询迁移到共享连接；HTTP 写响应先更新投影，再由事件按 version 对账。
9. 完成协议、权限、乱序、恢复、多实例、慢消费者和真实浏览器/代理测试，回填 Acceptance 后再移除正常路径轮询。

## 2. DAC/AC 映射

| 契约 | 实现 | 验证 |
| --- | --- | --- |
| DAC-014-01 / AC-014-01 | 共享 WebSocket 管理器替换固定轮询 | fake timer、请求计数和真实浏览器网络记录 |
| DAC-014-02 | 状态+event+Outbox 同事务 | repository crash/rollback 和 RabbitMQ 不可用测试 |
| DAC-014-03 / AC-014-02 | 握手认证、Origin、owner 订阅校验 | 401/403/close code、跨用户存在性测试 |
| DAC-014-04 / AC-014-03 | 单调 version reducer | 重复、乱序、延迟 run/event 测试 |
| DAC-014-05/06 / AC-014-04/05 | 有限重放/快照、缓冲接管、resync | 断线窗口、Gateway restart、多实例竞态测试 |
| DAC-014-07 / AC-014-06 | 有界发送队列、按 task 合并进度 | 慢客户端、队列上限、终态不丢测试 |
| DAC-014-08 / AC-014-09 | 严格公开投影与脱敏日志 | schema 禁止字段、URL/日志扫描 |
| DAC-014-09 / AC-014-07 | 指数退避和低频 HTTP fallback | broker/socket 故障与恢复后停止轮询测试 |
| DAC-014-10 / AC-014-08/10 | 单例连接、页面状态、完整 E2E | 多页/多任务、桌面/移动、键盘和 a11y 验收 |

## 3. 后端测试覆盖

- 协议解析拒绝未知 type/version、重复任务、非法 after_version、任意 channel、超限数组和超大帧。
- 握手覆盖缺 Cookie、过期 token、禁用账户、错误 Origin/Host、生产非 TLS 和连接数限制。
- 订阅覆盖 owner、跨用户 UUID、删除中任务、重复订阅、取消订阅及会话角色变化。
- task_events 覆盖 version 联合唯一、事务回滚、保留窗口、有限重放、快照 fallback 和历史清理。
- Gateway 覆盖 RabbitMQ 重投、多实例广播、连接缓冲竞态、心跳超时、慢消费者和优雅 shutdown。
- 日志/指标只使用低基数 ID 与错误码，不记录 Cookie、JWT、完整 payload、报告或签名 URL。

## 4. 前端与浏览器测试

- 单例连接按认证 owner 创建和销毁；登出/切换用户清空版本与订阅，不跨会话复用状态。
- reducer 按 task version 应用相邻事件，丢弃旧事件，缺口暂停应用并 resync；run_no 不能被旧代次覆盖。
- 重连使用带抖动指数退避，短时断线只显示连接状态；永久失败提供重连和手动刷新。
- HTTP create/retry/cancel 响应立即可见，之后事件对账；报告只有 `available` 才启用下载。
- 网络记录证明正常路径无固定周期查询；断网时降级查询有退避，恢复后停止。
- 覆盖多标签页、页面休眠、网络切换、1280px/390×844、键盘、aria-live 节流和 reduced motion。

## 5. 发布与回滚

- 先部署 version/task_events 写入和 Outbox，再部署 Gateway，最后启用前端 WebSocket 并移除高频轮询。
- 协议切换以单一 `protocol_version` 原子发布，不长期维护多版本双轨；版本不兼容时客户端降级并提示刷新。
- Gateway 可独立停用，前端进入低频 HTTP 恢复；不得回退为原 1.5 秒正常轮询。

## 6. 不做项

不增加任意 pub/sub API、不让浏览器连接 RabbitMQ、不通过 WebSocket 写任务或传输大文件、不无限保留事件，也不将在线连接状态写成任务状态。
