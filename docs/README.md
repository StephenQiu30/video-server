# 文档索引

根目录 `docs/` 是 `server` 的唯一产品与技术事实来源。

外部依赖与方案选型记录在 [`research/`](research/)；下载内核选型见 [GitHub 开源方案调研](research/001-GitHub开源方案调研.md)，公网产品完备性、开源整合与优先级见 [上线能力与 GitHub 开源整合调研](research/002-上线能力与GitHub开源整合调研.md)，Cookie、PO Token、出口一致性和逐平台适配见 [多平台下载会话与 GitHub 适配调研](research/003-多平台下载会话与GitHub适配调研.md)。

根目录 Compose 的使用与安全边界见 [运行手册](operations/001-root-compose运行手册.md)。

交付顺序固定为 `Design → PRD → Plan → Acceptance`：

| 编号 | 主题 | Design | PRD | Plan | Acceptance |
| --- | --- | --- | --- | --- | --- |
| 001 | 单仓与运行时架构 | [Design](design/001-server单仓与运行时架构设计.md) | [PRD](prd/001-server单仓与运行时架构需求.md) | [Plan](plans/001-server单仓与运行时架构计划.md) | [Acceptance](acceptance/001-server单仓与运行时架构验收.md) |
| 002 | 安全视频下载闭环 | [Design](design/002-安全视频下载闭环设计.md) | [PRD](prd/002-安全视频下载闭环需求.md) | [Plan](plans/002-安全视频下载闭环计划.md) | [Acceptance](acceptance/002-安全视频下载闭环验收.md) |
| 003 | AI 分析与思维导图 | [Design](design/003-AI分析与思维导图设计.md) | [PRD](prd/003-AI分析与思维导图需求.md) | [Plan](plans/003-AI分析与思维导图计划.md) | [Acceptance](acceptance/003-AI分析与思维导图验收.md) |
| 004 | 下载历史 | [Design](design/004-下载历史设计.md) | [PRD](prd/004-下载历史需求.md) | [Plan](plans/004-下载历史计划.md) | [Acceptance](acceptance/004-下载历史验收.md) |
| 005 | 多平台 Provider 与会话适配 | [Design](design/005-多平台Provider策略设计.md) | [PRD](prd/005-多平台Provider与会话适配需求.md) | [Plan](plans/005-多平台Provider与会话适配计划.md) | [Acceptance](acceptance/005-多平台Provider与会话适配验收.md) |
| 006 | 上线产品能力补全 | [Design](design/006-上线产品能力补全设计.md) | [PRD](prd/006-上线产品能力补全需求.md) | [Plan](plans/006-上线产品能力补全计划.md) | [Acceptance](acceptance/006-上线产品能力补全验收.md) |
| 007 | 邮箱账户与 JWT 认证 | [Design](design/007-邮箱账户与JWT认证设计.md) | [PRD](prd/007-邮箱账户与JWT认证需求.md) | [Plan](plans/007-邮箱账户与JWT认证计划.md) | [Acceptance](acceptance/007-邮箱账户与JWT认证验收.md) |
| 008 | 用户资料与角色管理 | [Design](design/008-用户资料与角色管理设计.md) | [PRD](prd/008-用户资料与角色管理需求.md) | [Plan](plans/008-用户资料与角色管理计划.md) | [Acceptance](acceptance/008-用户资料与角色管理验收.md) |
| 009 | Next 前端与页面重设计 | [Design](design/009-Next前端与蓝白视觉系统设计.md) | [PRD](prd/009-前端体验重构需求.md) | [Plan](plans/009-前端迁移与页面重设计计划.md) | [Acceptance](acceptance/009-前端迁移与页面重设计验收.md) |
| 010 | Codex 与 Claude CLI 视频分析 | [Design](design/010-Codex与Claude CLI视频分析设计.md) | [PRD](prd/010-Codex与Claude CLI视频分析需求.md) | [Plan](plans/010-Codex与Claude CLI视频分析迁移计划.md) | [Acceptance](acceptance/010-Codex与Claude CLI视频分析验收.md) |
| 011 | 管理员下载数据分析 | [Design](design/011-管理员下载数据分析设计.md) | [PRD](prd/011-管理员下载数据分析需求.md) | [Plan](plans/011-管理员下载数据分析计划.md) | [Acceptance](acceptance/011-管理员下载数据分析验收.md) |
