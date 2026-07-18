# video-server 执行文档

本仓库以 `Design → PRD → Plan → Acceptance → Implementation` 为唯一产品事实链。用户最新明确顺序覆盖重置期的旧模板顺序；Implementation 只能执行状态为 `ready` 的 Plan，并逐项回填对应 Acceptance。

## 当前产品

产品定义为“授权视频下载与 AI 知识化工作台”。“万能”表示统一入口和可扩展适配器，不包含 DRM、登录墙、付费墙、平台禁用下载或其他限制绕过。

## 文档索引

### Design

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [001 产品设计](design/001-授权视频下载与AI知识化产品设计.md) | accepted | 定位、旅程、合规与内容编排 |
| [002 服务端架构](design/002-服务端技术与数据架构设计.md) | accepted | 技术、模块、数据与运行拓扑 |
| [003 API 契约](design/003-API与任务状态契约设计.md) | accepted | API、状态、事件、错误与幂等 |
| [004 Plan 001 细化](design/004-Plan001来源解析安全与持久化设计.md) | accepted | 主体、数据、政策、出站和可靠性 |

### PRD

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [001 MVP](prd/001-授权视频下载与AI知识化MVP.md) | accepted | P0/P1、需求 ID、指标与非目标 |

### Plan

| 文档 | 状态 | 责任 |
| --- | --- | --- |
| [001 URL 解析](plans/001-URL异步解析与清晰度目录计划.md) | ready | 安全异步解析与真实清晰度目录 |
| [002 下载交付](plans/002-清晰度下载与媒体交付计划.md) | backlog | 下载、合流、校验和对象存储 |
| [003 AI 内容](plans/003-AI转录总结与思维导图计划.md) | backlog | 转写、摘要、证据和思维导图 |
| [004 PDF](plans/004-PDF导出与生命周期计划.md) | backlog | 编辑、PDF、删除和生命周期 |
| [005 生产加固](plans/005-生产兼容性与安全加固计划.md) | backlog | 容量、兼容、安全与多模态评估 |

### Acceptance

| 文档 | 文档状态 | 结果 |
| --- | --- | --- |
| [000 MVP 总览](acceptance/000-MVP验收总览.md) | accepted | pending |
| [001 URL 解析](acceptance/001-URL解析与清晰度目录验收.md) | accepted | pending |

## 状态规则

- Design/PRD：`draft → review → accepted → superseded`。
- Plan：`draft → review → ready → in_progress → done`，未来工作保持 `backlog`。
- Acceptance 文档状态：`draft → accepted`；执行结果：`pending → passed/failed/blocked`。
- 缺少输入、批准状态或可执行验收时，Plan 不得进入 `ready`。
- 文档只保存稳定契约和证据，不创建 `.planning`、日记或重复流程目录。

`TEMPLATE.md` 提供通用结构，不代表产品决策。
