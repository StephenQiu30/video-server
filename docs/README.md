# 文档索引

根目录 `docs/` 是 `server` 的唯一产品与技术事实来源。

所有未归档编号的原因、剩余交付任务与归档顺序统一维护在 [归档路线与技术债清单](ARCHIVE_ROADMAP.md)。`research/` 和 `operations/` 是持续维护的当前事实与运行手册，不属于编号交付四件套的归档目标。

外部依赖与方案选型记录在 [`research/`](research/)；下载内核选型见 [GitHub 开源方案调研](research/001-GitHub开源方案调研.md)，公网产品完备性、开源整合与优先级见 [上线能力与 GitHub 开源整合调研](research/002-上线能力与GitHub开源整合调研.md)，Cookie、PO Token、出口一致性和逐平台适配见 [多平台下载会话与 GitHub 适配调研](research/003-多平台下载会话与GitHub适配调研.md)，短视频提取与集成方案见 [GitHub 短视频提取方案调研](research/004-GitHub短视频提取方案调研.md)，其他短视频/社交视频平台的 extractor、维护状态、许可与接入优先级见 [其他短视频平台接入调研](research/005-其他短视频平台接入调研.md)，Facebook 分享帖子解析适配见 [Facebook 分享帖子解析调研](research/006-Facebook分享帖子解析调研.md)，RabbitMQ producer/consumer、quorum、DLQ 与可观测性选型见 [RabbitMQ 可靠投递 GitHub 调研](research/006-RabbitMQ可靠投递GitHub调研.md)，剩余 Provider 的逐平台能力验证见 [剩余 Provider 逐平台验证调研](research/007-剩余Provider逐平台验证调研.md)，主流社交媒体 Provider 扩展方向见 [主流社交媒体 Provider 扩展调研](research/008-主流社交媒体Provider扩展调研.md)，红果官方 App、开源设备采集器、DRM 与 Edge Agent 路径见 [红果短剧 Provider 接入调研](research/009-红果短剧Provider接入调研.md)，微信视频号本地代理、分享链接、媒体转换和 Edge Agent 架构见 [微信视频号 Provider 接入调研](research/010-微信视频号Provider接入调研.md)。

宿主机 Analysis Agent、项目内 Provider Profile 与跨平台常驻方案见 [AI 分析 Agent 与通用 Provider 接入调研](research/011-AI分析Agent与通用Provider接入调研.md)；浏览器本地文件上传、剧本文档解析、GitHub Skill 复用与中英文改写边界见 [本地内容上传与剧本 Skill 调研](research/012-本地内容上传与剧本Skill调研.md)。

根目录 Compose 的使用与安全边界见 [运行手册](operations/001-root-compose运行手册.md)；YouTube 运维会话的账号基线、Secret 导入、启动、轮换、撤销和脱敏验收见 [YouTube 受控会话运行手册](operations/002-YouTube受控会话运行手册.md)；TikTok、Instagram、Facebook、X、Reddit 与 Vimeo 的逐 Provider 隔离部署见 [多平台受控会话运行手册](operations/003-多平台受控会话运行手册.md)；本地 CI 命令、GitHub 检查、运行边界和失败恢复见 [CI 与主分支门禁运行手册](operations/004-CI与主分支门禁运行手册.md)；从已登录浏览器安全导出会话并启动 Docker Operator Runner 见 [Docker 浏览器会话运行手册](operations/006-Docker浏览器会话运行手册.md)。

交付顺序固定为 `Design → PRD → Plan → Acceptance`：

当前增量设计：前端统一 BasicLayout 与共享内容网格见 [025 前端统一 BasicLayout 布局设计](design/025-前端统一BasicLayout布局设计.md)。该文档只覆盖现有前端的布局治理，不新增业务能力。


| 编号 | 主题 | Design | PRD | Plan | Acceptance |
| --- | --- | --- | --- | --- | --- |
| 001 | 单仓与运行时架构（已归档） | [Design](design/archive/001-server单仓与运行时架构设计.md) | [PRD](prd/archive/001-server单仓与运行时架构需求.md) | [Plan](plans/archive/001-server单仓与运行时架构计划.md) | [Acceptance](acceptance/archive/001-server单仓与运行时架构验收.md) |
| 002 | 安全视频下载闭环（已归档） | [Design](design/archive/002-安全视频下载闭环设计.md) | [PRD](prd/archive/002-安全视频下载闭环需求.md) | [Plan](plans/archive/002-安全视频下载闭环计划.md) | [Acceptance](acceptance/archive/002-安全视频下载闭环验收.md) |
| 004 | 下载历史（已归档） | [Design](design/archive/004-下载历史设计.md) | [PRD](prd/archive/004-下载历史需求.md) | [Plan](plans/archive/004-下载历史计划.md) | [Acceptance](acceptance/archive/004-下载历史验收.md) |
| 005 | 多平台 Provider 与会话适配 | [Design](design/005-多平台Provider策略设计.md) | [PRD](prd/005-多平台Provider与会话适配需求.md) | [Plan](plans/005-多平台Provider与会话适配计划.md) | [Acceptance](acceptance/005-多平台Provider与会话适配验收.md) |
| 006 | 上线产品能力补全 | [Design](design/006-上线产品能力补全设计.md) | [PRD](prd/006-上线产品能力补全需求.md) | [Plan](plans/006-上线产品能力补全计划.md) | [Acceptance](acceptance/006-上线产品能力补全验收.md) |
| 007 | 邮箱账户与 JWT 认证（已归档） | [Design](design/archive/007-邮箱账户与JWT认证设计.md) | [PRD](prd/archive/007-邮箱账户与JWT认证需求.md) | [Plan](plans/archive/007-邮箱账户与JWT认证计划.md) | [Acceptance](acceptance/archive/007-邮箱账户与JWT认证验收.md) |
| 008 | 用户资料与角色管理（已归档） | [Design](design/archive/008-用户资料与角色管理设计.md) | [PRD](prd/archive/008-用户资料与角色管理需求.md) | [Plan](plans/archive/008-用户资料与角色管理计划.md) | [Acceptance](acceptance/archive/008-用户资料与角色管理验收.md) |
| 009 | Next 前端与页面重设计（已归档） | [Design](design/archive/009-Next前端与蓝白视觉系统设计.md) | [PRD](prd/archive/009-前端体验重构需求.md) | [Plan](plans/archive/009-前端迁移与页面重设计计划.md) | [Acceptance](acceptance/archive/009-前端迁移与页面重设计验收.md) |
| 010 | Codex 与 Claude CLI 视频分析 | [Design](design/010-Codex与Claude CLI视频分析设计.md) | [PRD](prd/010-Codex与Claude CLI视频分析需求.md) | [Plan](plans/010-Codex与Claude CLI视频分析迁移计划.md) | [Acceptance](acceptance/010-Codex与Claude CLI视频分析验收.md) |
| 011 | 管理员下载数据分析（已归档） | [Design](design/archive/011-管理员下载数据分析设计.md) | [PRD](prd/archive/011-管理员下载数据分析需求.md) | [Plan](plans/archive/011-管理员下载数据分析计划.md) | [Acceptance](acceptance/archive/011-管理员下载数据分析验收.md) |
| 012 | AI 分析报告与 MinIO 持久化（已归档） | [Design](design/archive/012-AI分析报告与MinIO持久化设计.md) | [PRD](prd/archive/012-AI分析报告与MinIO持久化需求.md) | [Plan](plans/archive/012-AI分析报告与MinIO持久化计划.md) | [Acceptance](acceptance/archive/012-AI分析报告与MinIO持久化验收.md) |
| 013 | AI 分析原任务重试（已归档） | [Design](design/archive/013-AI分析原任务重试设计.md) | [PRD](prd/archive/013-AI分析原任务重试需求.md) | [Plan](plans/archive/013-AI分析原任务重试计划.md) | [Acceptance](acceptance/archive/013-AI分析原任务重试验收.md) |
| 014 | WebSocket 任务状态同步（已归档） | [Design](design/archive/014-WebSocket任务状态同步设计.md) | [PRD](prd/archive/014-WebSocket任务状态同步需求.md) | [Plan](plans/archive/014-WebSocket任务状态同步计划.md) | [Acceptance](acceptance/archive/014-WebSocket任务状态同步验收.md) |
| 015 | RabbitMQ 异步分析与可靠投递（已归档） | [Design](design/archive/015-RabbitMQ异步分析设计.md) | [PRD](prd/archive/015-RabbitMQ异步分析需求.md) | [Plan](plans/archive/015-RabbitMQ异步分析计划.md) | [Acceptance](acceptance/archive/015-RabbitMQ异步分析验收.md) |
| 016 | 中国短视频平台支持（已归档） | [Design](design/archive/016-中国短视频平台支持设计.md) | [PRD](prd/archive/016-中国短视频平台支持需求.md) | [Plan](plans/archive/016-中国短视频平台支持计划.md) | [Acceptance](acceptance/archive/016-中国短视频平台支持验收.md) |
| 017 | 其他短视频平台分阶段接入 | [Design](design/017-其他短视频平台分阶段接入设计.md) | [PRD](prd/017-其他短视频平台分阶段接入需求.md) | [Plan](plans/017-其他短视频平台分阶段接入计划.md) | [Acceptance](acceptance/017-其他短视频平台分阶段接入验收.md) |
| 018 | RabbitMQ 生产可靠性增强（已归档） | [Design](design/archive/018-RabbitMQ生产可靠性增强设计.md) | [PRD](prd/archive/018-RabbitMQ生产可靠性增强需求.md) | [Plan](plans/archive/018-RabbitMQ生产可靠性增强计划.md) | [Acceptance](acceptance/archive/018-RabbitMQ生产可靠性增强验收.md) |
| 019 | 用户设备 Edge Agent 与媒体制品导入 | [Design](design/019-用户设备EdgeAgent与媒体制品导入设计.md) | [PRD](prd/019-用户设备EdgeAgent与媒体制品导入需求.md) | [Plan](plans/019-用户设备EdgeAgent与媒体制品导入计划.md) | [Acceptance](acceptance/019-用户设备EdgeAgent与媒体制品导入验收.md) |
| 020 | 用户制品持久化与保留策略（已归档） | [Design](design/archive/020-用户制品持久化与保留策略设计.md) | [PRD](prd/archive/020-用户制品持久化与保留策略需求.md) | [Plan](plans/archive/020-用户制品持久化与保留策略计划.md) | [Acceptance](acceptance/archive/020-用户制品持久化与保留策略验收.md) |
| 021 | 媒体封面持久化（已归档） | [Design](design/archive/021-媒体封面持久化设计.md) | [PRD](prd/archive/021-媒体封面持久化需求.md) | [Plan](plans/archive/021-媒体封面持久化计划.md) | [Acceptance](acceptance/archive/021-媒体封面持久化验收.md) |
| 022 | 跨平台 AI 分析 Agent 与模型 Provider 配置 | [Design](design/022-跨平台AI分析Agent与模型Provider配置设计.md) | [PRD](prd/022-跨平台AI分析Agent与模型Provider配置需求.md) | [Plan](plans/022-跨平台AI分析Agent与模型Provider配置计划.md) | [Acceptance](acceptance/022-跨平台AI分析Agent与模型Provider配置验收.md) |
| 023 | 本地内容上传与剧本分析 | [Design](design/023-本地内容上传与剧本分析设计.md) | [PRD](prd/023-本地内容上传与剧本分析需求.md) | [Plan](plans/023-本地内容上传与剧本分析计划.md) | [Acceptance](acceptance/023-本地内容上传与剧本分析验收.md) |
| 024 | Docker 浏览器会话桥接（已归档） | [Design](design/archive/024-Docker浏览器会话桥接设计.md) | [PRD](prd/archive/024-Docker浏览器会话桥接需求.md) | [Plan](plans/archive/024-Docker浏览器会话桥接计划.md) | [Acceptance](acceptance/archive/024-Docker浏览器会话桥接验收.md) |
