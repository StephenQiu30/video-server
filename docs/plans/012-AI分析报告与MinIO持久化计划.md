# 012 AI 分析报告与 MinIO 持久化计划

- 状态：Completed
- 日期：2026-08-10
- 关联 Design：`docs/design/012-AI分析报告与MinIO持久化设计.md`
- 关联 PRD：`docs/prd/012-AI分析报告与MinIO持久化需求.md`
- 依赖：013 执行代次模型；015 报告发布队列
- 完成证据：`docs/acceptance/012-AI分析报告与MinIO持久化验收.md`

## 1. 实施顺序

1. 冻结报告状态、renderer version、两个格式、错误码、对象键和公开 API 白名单，并补 OpenAPI 契约测试。
2. 在当前态 SQL、ORM 和 repository 中引入 `analysis_report_versions`、`analysis_report_artifacts` 与 `analysis_jobs.current_report_id`，收敛现有单条 `analysis_results` 写入事实。
3. 把当前 Markdown 生成逻辑提炼为确定性 canonical renderer，DOCX 只能消费该 Markdown；为同一输入增加字节级或语义哈希回归测试。
4. 在 AI 结果提交事务中写入 `validated` 报告版本、任务事件和唯一 `analysis.report.publish.requested` Outbox。
5. 实现独立 Report Publisher：数据库租约 claim、确定性对象键、生成、SHA-256、MinIO Put/Stat 校验、发布确认和故障恢复。
6. 将报告查询接口改为读取当前可用 artifact；完成 owner 授权后短时重定向或受控流式代理，不再即时渲染。
7. 实现 `publish_failed → publishing` 恢复、数据库/MinIO 对账、孤儿隔离和生命周期删除 Worker。
8. 更新前端任务投影与报告区，区分 `publishing`、`available`、`publish_failed`、上一版本和对象不可用状态。
9. 完成数据库、MinIO、队列、API、前端和故障注入测试，使用真实 `.md/.docx` 下载验证后回填 Acceptance。

## 2. DAC/AC 映射

| 契约 | 实现 | 验证 |
| --- | --- | --- |
| DAC-012-01/02 / AC-012-01/02 | 版本表、canonical Markdown、双格式 artifact | renderer 确定性、重启恢复、对象内容/哈希测试 |
| DAC-012-03 / AC-012-03 | `validated → publishing → available` 状态机 | 单/双对象缺失、发布完成事务测试 |
| DAC-012-04/05 / AC-012-04 | 确定性键、租约、Put/Stat、幂等 Outbox 消费 | 重复消息与各故障点 crash/restart 测试 |
| DAC-012-06 / AC-012-05/10 | owner 授权、私有 bucket、短时下载响应 | 401/404、跨用户、过期签名、header 测试 |
| DAC-012-07 / AC-012-07 | `current_report_id` 延迟原子切换 | 新 run 成功/失败/取消并发测试 |
| DAC-012-08 / AC-012-06 | 对象对账与稳定错误 | 删除对象后的 503、告警与禁止即时重建测试 |
| DAC-012-09 / AC-012-08 | `delete_pending`、Lifecycle Worker、孤儿隔离 | 重复删除、半失败、TTL 与孤儿清理测试 |
| DAC-012-10 / AC-012-09 | 严格 schema、日志/事件白名单、全链门禁 | OpenAPI、脱敏、SQL/ORM、MinIO 集成与 E2E |

## 3. 后端工作包与测试

- Domain/Application：报告版本状态机、格式枚举、哈希/大小限制、发布 claim、当前报告切换和稳定错误映射。
- Persistence：空库与已有当前态库幂等执行 schema；唯一 run/report、report/format 和对象键约束；repository 并发测试。
- Renderer：Markdown 快照唯一来源，DOCX 无宏/远程关系/本机路径；固定输入的哈希、段落和表格结构回归。
- MinIO：私有 bucket、Put/Stat/Get/Delete、错误分类、超时/大小限制、同键不同内容 fail closed。
- Queue：报告消息重复、乱序、publisher confirm、ACK 前 crash、上传后 crash、DLQ 与恢复。
- API：严格投影、`409 analysis_report_not_ready`、`503 analysis_report_unavailable`、owner 404、内容类型和 Content-Disposition。
- Security：URL/日志/事件不含 bucket、object key、签名参数、报告正文、Prompt 或 Secret。

## 4. 前端与浏览器验证

- 任务详情准确展示发布中、可下载、发布失败、对象不可用和上一版本，不用 `progress == 100` 推断可下载。
- Markdown 与 DOCX 两个入口展示真实大小和格式；请求失败保留重试，不把存储错误误报为 AI 失败。
- 覆盖加载、刷新、旧报告+新 run、键盘操作、屏幕阅读器名称、1280px 与 390×844 无溢出。
- 下载真实文件并分别用文本读取器和 Word/LibreOffice 打开，核对同源内容、文件名和媒体类型。

## 5. 发布与回滚

- 同一发布同步 SQL、ORM、repository 和消费者，先部署可处理报告消息的 Publisher，再启用新的 Outbox 事件。
- bucket policy 和服务账号先以最小权限验证；不得把个人 CLI OAuth 交给 Report Publisher。
- 发布失败时可停止报告消费者并保留 Outbox/`validated` 事实，不能回退到请求时即时渲染形成双写。

## 6. 不做项

不增加迁移目录、公开 bucket、数据库 DOCX BLOB、第二套报告正文、按下载请求重新渲染、PDF/模板编辑或跨报告合并。
