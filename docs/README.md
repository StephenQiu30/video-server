# 文档索引

`docs/` 当前只保留仍需维护的产品、技术和运行事实。本次已清理的历史 Design/PRD/Plan/Acceptance 通过 Git 追溯；后续完成态文档仍按仓库归档门禁处理。

## 当前事实

- [前端视觉系统](design/frontend-visual-system.md)：Next.js、Vercel/Geist 无边框视觉、响应式和可访问性规范。
- [媒体解析策略](design/media-source-strategy.md)：解析责任链、错误优先级、封面认证交付与 Provider Session Broker。
- [Provider 接入架构重构调研](research/008-Provider接入架构重构调研.md)：yt-dlp 官方扩展边界、现有耦合和声明式接入结论。
- [微信与腾讯授权媒体调研](research/014-微信视频号与腾讯视频授权媒体下载调研.md)：公众号文章原生视频、视频号 GitHub 方案、腾讯消费站权益与腾讯云 VOD 官方边界。
- [微信视频号公开分享链接服务端解析调研](research/015-微信视频号公开分享链接服务端解析调研.md)：匿名公开性预检、隔离元宝会话、媒体白名单与保护拒绝。
- [`design/`](design/)：尚未完成或仍需持续维护的设计事实。
- [`prd/`](prd/)：当前需求与产品边界。
- [`plans/`](plans/)：仍在执行的交付计划。
- [`acceptance/`](acceptance/)：仍有待验证条件的验收门禁。
- [`research/`](research/)：仍影响当前实现的外部依赖、平台能力和方案调研。
- [`operations/`](operations/)：当前部署、运行、安全和故障恢复手册。
- [`images/`](images/)：根 README 正在使用的产品截图。

## 当前交付编号

| 编号 | 主题 | Design | PRD | Plan | Acceptance |
| --- | --- | --- | --- | --- | --- |
| 005 | 多平台 Provider 与会话适配 | [Design](design/005-多平台Provider策略设计.md) | [PRD](prd/005-多平台Provider与会话适配需求.md) | [Plan](plans/005-多平台Provider与会话适配计划.md) | [Acceptance](acceptance/005-多平台Provider与会话适配验收.md) |
| 006 | 上线产品能力补全 | [Design](design/006-上线产品能力补全设计.md) | [PRD](prd/006-上线产品能力补全需求.md) | [Plan](plans/006-上线产品能力补全计划.md) | [Acceptance](acceptance/006-上线产品能力补全验收.md) |
| 010 | Codex 与 Claude CLI 视频分析 | [Design](design/010-Codex与Claude CLI视频分析设计.md) | [PRD](prd/010-Codex与Claude CLI视频分析需求.md) | [Plan](plans/010-Codex与Claude CLI视频分析迁移计划.md) | [Acceptance](acceptance/010-Codex与Claude CLI视频分析验收.md) |
| 017 | 其他短视频平台分阶段接入 | [Design](design/017-其他短视频平台分阶段接入设计.md) | [PRD](prd/017-其他短视频平台分阶段接入需求.md) | [Plan](plans/017-其他短视频平台分阶段接入计划.md) | [Acceptance](acceptance/017-其他短视频平台分阶段接入验收.md) |
| 019 | 用户设备 Edge Agent 与媒体制品导入 | [Design](design/019-用户设备EdgeAgent与媒体制品导入设计.md) | [PRD](prd/019-用户设备EdgeAgent与媒体制品导入需求.md) | [Plan](plans/019-用户设备EdgeAgent与媒体制品导入计划.md) | [Acceptance](acceptance/019-用户设备EdgeAgent与媒体制品导入验收.md) |
| 022 | 跨平台 AI 分析 Agent 与模型 Provider 配置 | [Design](design/022-跨平台AI分析Agent与模型Provider配置设计.md) | [PRD](prd/022-跨平台AI分析Agent与模型Provider配置需求.md) | [Plan](plans/022-跨平台AI分析Agent与模型Provider配置计划.md) | [Acceptance](acceptance/022-跨平台AI分析Agent与模型Provider配置验收.md) |
| 023 | 本地内容上传与剧本分析 | [Design](design/023-本地内容上传与剧本分析设计.md) | [PRD](prd/023-本地内容上传与剧本分析需求.md) | [Plan](plans/023-本地内容上传与剧本分析计划.md) | [Acceptance](acceptance/023-本地内容上传与剧本分析验收.md) |
| 024 | 微信公众号文章、视频号与腾讯授权媒体接入 | [Design](design/024-微信视频号与腾讯视频授权媒体接入设计.md) | [PRD](prd/024-微信视频号与腾讯视频授权媒体接入需求.md) | [Plan](plans/024-微信视频号与腾讯视频授权媒体接入计划.md) | [Acceptance](acceptance/024-微信视频号与腾讯视频授权媒体接入验收.md) |
| 025 | 微信视频号公开分享链接下载 | [Design](design/025-微信视频号公开分享链接下载设计.md) | [PRD](prd/025-微信视频号公开分享链接下载需求.md) | [Plan](plans/025-微信视频号公开分享链接下载计划.md) | [Acceptance](acceptance/025-微信视频号公开分享链接下载验收.md) |
