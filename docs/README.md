# video-server 执行文档

本仓库以 `Design → PRD → Plan → Acceptance → Implementation` 为唯一产品事实链。用户最新明确顺序覆盖重置期的旧模板顺序；Implementation 只能执行状态为 `ready` 的 Plan，并逐项回填对应 Acceptance。邮箱身份与持久化是新的基础门禁，未完成 Plan 000 前不得继续 Plan 001 的 API/worker 实现。

## 当前产品

产品定义为“授权视频下载与 AI 知识化工作台”。“万能”表示统一入口和可扩展适配器，不包含 DRM、登录墙、付费墙、平台禁用下载或其他限制绕过。用户以已验证邮箱登录；PostgreSQL 是唯一业务事实，Redis 可重建，MinIO 只保存私有二进制，SMTP 只负责邮件投递。

## 文档索引

### Design

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [001 产品设计](design/001-授权视频下载与AI知识化产品设计.md) | accepted | 定位、旅程、合规与内容编排；纳入邮箱身份/持久化 |
| [002 服务端架构](design/002-服务端技术与数据架构设计.md) | accepted | Python/FastAPI、PG、可重建 Redis、MinIO、SMTP |
| [003 API 契约](design/003-API与任务状态契约设计.md) | accepted | 身份、API、状态、事件、错误与幂等 |
| [004 Plan 001 细化](design/004-Plan001来源解析安全与持久化设计.md) | accepted | UUID owner、数据、政策、出站和可靠性 |
| [005 身份与持久化](design/005-邮箱身份与持久化基础设施设计.md) | accepted | 邮箱用户、会话、PG/Redis/MinIO/SMTP 与灾备 |

### PRD

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [001 MVP](prd/001-授权视频下载与AI知识化MVP.md) | accepted | P0/P1、需求 ID、指标与非目标 |

### Plan

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [000 身份与持久化](plans/000-邮箱身份与持久化基础设施计划.md) | ready | 邮箱会话、PG/Redis/MinIO/SMTP 基础门禁 |
| [001 URL 解析](plans/001-URL异步解析与清晰度目录计划.md) | review | 等待 Plan 000；保留 Resolution 局部 Green |
| [002 下载交付](plans/002-清晰度下载与媒体交付计划.md) | backlog | 下载、合流、校验和对象存储 |
| [003 AI 内容](plans/003-AI转录总结与思维导图计划.md) | backlog | 转写、摘要、证据和思维导图 |
| [004 PDF](plans/004-PDF导出与生命周期计划.md) | backlog | 编辑、PDF、删除和生命周期 |
| [005 生产加固](plans/005-生产兼容性与安全加固计划.md) | backlog | 容量、兼容、安全与多模态评估 |

### Acceptance

| 文档 | 文档状态 | 结果 |
| --- | --- | --- |
| [000 MVP 总览](acceptance/000-MVP验收总览.md) | draft | pending |
| [001 URL 解析](acceptance/001-URL解析与清晰度目录验收.md) | draft | pending |
| [002 身份与持久化](acceptance/002-邮箱身份与持久化基础设施验收.md) | accepted | pending |

## 状态规则

- Design/PRD：`draft → review → accepted → superseded`。
- Plan：`draft → review → ready → in_progress → done`，未来工作保持 `backlog`。
- Acceptance 文档状态：`draft → accepted`；执行结果：`pending → passed/failed/blocked`。
- 缺少输入、批准状态或可执行验收时，Plan 不得进入 `ready`。
- 文档只保存稳定契约和证据，不创建 `.planning`、日记或重复流程目录。
- 文档版本遵循 SemVer：已接受 `1.x` 契约的破坏性调整升 major；未冻结 `0.x` 的破坏性调整升 minor；兼容新增升 minor；澄清和证据回填升 patch。状态与版本相互独立，变更后必须重新复审才能恢复 `accepted/ready`。

当前执行唯一目标是已就绪的 Plan 000，并按用户/UUID owner → 会话/认证 → 邮件 → Redis/outbox → MinIO → 恢复 → OpenAPI 的 TDD 切片推进。Plan 001 的 557 项 Resolution/rights history 局部 Green 不是全链 Acceptance，不能绕过该门禁。

`TEMPLATE.md` 提供通用结构，不代表产品决策。
