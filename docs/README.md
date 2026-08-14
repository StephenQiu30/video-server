# 文档索引

根目录 `docs/` 是 `server` 的唯一产品与技术事实来源。

外部依赖与方案选型记录在 [`research/`](research/)；下载内核选型见 [GitHub 开源方案调研](research/001-GitHub开源方案调研.md)，公网产品完备性、开源整合与优先级见 [上线能力与 GitHub 开源整合调研](research/002-上线能力与GitHub开源整合调研.md)，Cookie、PO Token、出口一致性和逐平台适配见 [多平台下载会话与 GitHub 适配调研](research/003-多平台下载会话与GitHub适配调研.md)，短视频提取与集成方案见 [GitHub 短视频提取方案调研](research/004-GitHub短视频提取方案调研.md)，其他短视频/社交视频平台的 extractor、维护状态、许可与接入优先级见 [其他短视频平台接入调研](research/005-其他短视频平台接入调研.md)，Facebook 分享帖子解析适配见 [Facebook 分享帖子解析调研](research/006-Facebook分享帖子解析调研.md)，RabbitMQ producer/consumer、quorum、DLQ 与可观测性选型见 [RabbitMQ 可靠投递 GitHub 调研](research/006-RabbitMQ可靠投递GitHub调研.md)，剩余 Provider 的逐平台能力验证见 [剩余 Provider 逐平台验证调研](research/007-剩余Provider逐平台验证调研.md)，主流社交媒体 Provider 扩展方向见 [主流社交媒体 Provider 扩展调研](research/008-主流社交媒体Provider扩展调研.md)，红果官方 App、开源设备采集器、DRM 与 Edge Agent 路径见 [红果短剧 Provider 接入调研](research/009-红果短剧Provider接入调研.md)，微信视频号本地代理、分享链接、媒体转换和 Edge Agent 架构见 [微信视频号 Provider 接入调研](research/010-微信视频号Provider接入调研.md)。

根目录 Compose 的使用与安全边界见 [运行手册](operations/001-root-compose运行手册.md)；YouTube 运维会话的账号基线、Secret 导入、启动、轮换、撤销和脱敏验收见 [YouTube 受控会话运行手册](operations/002-YouTube受控会话运行手册.md)；TikTok、Instagram、Facebook、X、Reddit 与 Vimeo 的逐 Provider 隔离部署见 [多平台受控会话运行手册](operations/003-多平台受控会话运行手册.md)；本地 CI 命令、GitHub 检查、运行边界和失败恢复见 [CI 与主分支门禁运行手册](operations/004-CI与主分支门禁运行手册.md)。

交付顺序固定为 `Design → PRD → Plan → Acceptance`：

已完成真实验收的文档集先运行 `python scripts/archive_completed_docs.py` 只读检查，再通过 `python scripts/archive_completed_docs.py --apply` 移动到 `archive/<编号>/`；命令只接受 Design/PRD/Acceptance 为 `Accepted`、Plan 为 `Complete` 或 `Completed` 的完整四件套，并同步更新索引和仓库内引用，禁止手工移动形成部分归档状态。017 仍需额外通过 Provider 实测门禁和 `acceptance: accepted` 标记后使用专用 canary 归档命令。

| 编号 | 主题 | Design | PRD | Plan | Acceptance |
| --- | --- | --- | --- | --- | --- |
| 001 | 单仓与运行时架构（已归档） | [Design](archive/001/001-server单仓与运行时架构设计.md) | [PRD](archive/001/001-server单仓与运行时架构需求.md) | [Plan](archive/001/001-server单仓与运行时架构计划.md) | [Acceptance](archive/001/001-server单仓与运行时架构验收.md) |
| 002 | 安全视频下载闭环 | [Design](design/002-安全视频下载闭环设计.md) | [PRD](prd/002-安全视频下载闭环需求.md) | [Plan](plans/002-安全视频下载闭环计划.md) | [Acceptance](acceptance/002-安全视频下载闭环验收.md) |
| 004 | 下载历史 | [Design](design/004-下载历史设计.md) | [PRD](prd/004-下载历史需求.md) | [Plan](plans/004-下载历史计划.md) | [Acceptance](acceptance/004-下载历史验收.md) |
| 005 | 多平台 Provider 与会话适配 | [Design](design/005-多平台Provider策略设计.md) | [PRD](prd/005-多平台Provider与会话适配需求.md) | [Plan](plans/005-多平台Provider与会话适配计划.md) | [Acceptance](acceptance/005-多平台Provider与会话适配验收.md) |
| 006 | 上线产品能力补全 | [Design](design/006-上线产品能力补全设计.md) | [PRD](prd/006-上线产品能力补全需求.md) | [Plan](plans/006-上线产品能力补全计划.md) | [Acceptance](acceptance/006-上线产品能力补全验收.md) |
| 007 | 邮箱账户与 JWT 认证（已归档） | [Design](archive/007/007-邮箱账户与JWT认证设计.md) | [PRD](archive/007/007-邮箱账户与JWT认证需求.md) | [Plan](archive/007/007-邮箱账户与JWT认证计划.md) | [Acceptance](archive/007/007-邮箱账户与JWT认证验收.md) |
| 008 | 用户资料与角色管理 | [Design](design/008-用户资料与角色管理设计.md) | [PRD](prd/008-用户资料与角色管理需求.md) | [Plan](plans/008-用户资料与角色管理计划.md) | [Acceptance](acceptance/008-用户资料与角色管理验收.md) |
| 009 | Next 前端与页面重设计 | [Design](design/009-Next前端与蓝白视觉系统设计.md) | [PRD](prd/009-前端体验重构需求.md) | [Plan](plans/009-前端迁移与页面重设计计划.md) | [Acceptance](acceptance/009-前端迁移与页面重设计验收.md) |
| 010 | Codex 与 Claude CLI 视频分析 | [Design](design/010-Codex与Claude CLI视频分析设计.md) | [PRD](prd/010-Codex与Claude CLI视频分析需求.md) | [Plan](plans/010-Codex与Claude CLI视频分析迁移计划.md) | [Acceptance](acceptance/010-Codex与Claude CLI视频分析验收.md) |
| 011 | 管理员下载数据分析 | [Design](design/011-管理员下载数据分析设计.md) | [PRD](prd/011-管理员下载数据分析需求.md) | [Plan](plans/011-管理员下载数据分析计划.md) | [Acceptance](acceptance/011-管理员下载数据分析验收.md) |
| 012 | AI 分析报告与 MinIO 持久化（已归档） | [Design](archive/012/012-AI分析报告与MinIO持久化设计.md) | [PRD](archive/012/012-AI分析报告与MinIO持久化需求.md) | [Plan](archive/012/012-AI分析报告与MinIO持久化计划.md) | [Acceptance](archive/012/012-AI分析报告与MinIO持久化验收.md) |
| 013 | AI 分析原任务重试（已归档） | [Design](archive/013/013-AI分析原任务重试设计.md) | [PRD](archive/013/013-AI分析原任务重试需求.md) | [Plan](archive/013/013-AI分析原任务重试计划.md) | [Acceptance](archive/013/013-AI分析原任务重试验收.md) |
| 014 | WebSocket 任务状态同步（已归档） | [Design](archive/014/014-WebSocket任务状态同步设计.md) | [PRD](archive/014/014-WebSocket任务状态同步需求.md) | [Plan](archive/014/014-WebSocket任务状态同步计划.md) | [Acceptance](archive/014/014-WebSocket任务状态同步验收.md) |
| 015 | RabbitMQ 异步分析与可靠投递（已归档） | [Design](archive/015/015-RabbitMQ异步分析设计.md) | [PRD](archive/015/015-RabbitMQ异步分析需求.md) | [Plan](archive/015/015-RabbitMQ异步分析计划.md) | [Acceptance](archive/015/015-RabbitMQ异步分析验收.md) |
| 016 | 中国短视频平台支持 | [Design](design/016-中国短视频平台支持设计.md) | 待补 | 待补 | [Acceptance](acceptance/016-中国短视频平台支持验收.md) |
| 017 | 其他短视频平台分阶段接入 | [Design](design/017-其他短视频平台分阶段接入设计.md) | [PRD](prd/017-其他短视频平台分阶段接入需求.md) | [Plan](plans/017-其他短视频平台分阶段接入计划.md) | [Acceptance](acceptance/017-其他短视频平台分阶段接入验收.md) |
| 018 | RabbitMQ 生产可靠性增强 | [Design](design/018-RabbitMQ生产可靠性增强设计.md) | 待补 | 待补 | 待补 |
| 019 | 用户设备 Edge Agent 与媒体制品导入 | [Design](design/019-用户设备EdgeAgent与媒体制品导入设计.md) | [PRD](prd/019-用户设备EdgeAgent与媒体制品导入需求.md) | [Plan](plans/019-用户设备EdgeAgent与媒体制品导入计划.md) | [Acceptance](acceptance/019-用户设备EdgeAgent与媒体制品导入验收.md) |
| 020 | 用户制品持久化与保留策略（已归档） | [Design](archive/020/020-用户制品持久化与保留策略设计.md) | [PRD](archive/020/020-用户制品持久化与保留策略需求.md) | [Plan](archive/020/020-用户制品持久化与保留策略计划.md) | [Acceptance](archive/020/020-用户制品持久化与保留策略验收.md) |
| 022 | 跨平台 AI 分析 Agent 与模型 Provider 配置 | [Design](design/022-跨平台AI分析Agent与模型Provider配置设计.md) | [PRD](prd/022-跨平台AI分析Agent与模型Provider配置需求.md) | [Plan](plans/022-跨平台AI分析Agent与模型Provider配置计划.md) | [Acceptance](acceptance/022-跨平台AI分析Agent与模型Provider配置验收.md) |
