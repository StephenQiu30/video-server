# 文档索引

- [内容创作与平台发布能力调研](research/023-内容创作与平台发布能力调研.md)：基于当前源码及 GitHub、Firecrawl、Context7 的文章/小红书能力审查、Skill 候选与官方发布边界；[036 设计](design/036-内容创作与平台发布设计.md) · [需求](prd/036-内容创作与平台发布需求.md) · [实施 SOP](plans/036-内容创作与平台发布计划.md) · [验收](acceptance/036-内容创作与平台发布验收.md)。研究与设计完成，新增功能尚未实施。

- [可迁移下载服务与平台会话架构调研](research/022-可迁移下载服务与平台会话架构调研.md)：GitHub、Firecrawl、Context7 一手资料与源码对照；区分客户端换机和服务迁移，明确项目独立来源、平台适配、六个实施切片及失败边界。方案已整理，新增来源与换机尚未实现/验收。

- [下载故障修复与持续可用性 SOP](operations/009-下载故障修复与持续可用性SOP.md)：按当前仓库规范执行接报、分层诊断、四份文档对齐、TDD、候选验证、部署、重启/文件验收、回滚和缺陷关闭；公共出口、登录误归因和 Web 页面刷新已有分项修复；平台来源与换机仍按 035 逐项验收。

- [下载可靠性与重启会话故障深度调研](research/021-下载可靠性与重启会话故障深度调研.md)：2026-09-15 实测定位 Squid 残留 PID 重启循环，复现 Fresh cookies 登录误分类；包含 23 平台维护策略、修复切片与验收矩阵。公共出口等修复进度见 035 验收第 23–27 节；全平台与换机仍未通过。

`docs/` 当前只保留仍需维护的产品、技术和运行事实。事实已经合并到长期文档的纯过程文件直接删除并通过 Git 追溯；只有仍具长期查阅价值的完成态文档才保留归档。

## 当前事实

- [代码质量问题与修复登记](code-quality.md)：跨 Server/Web/App 的缺陷、重复规则与设计复杂度裁决；首批修复已实施，按证据逐项关闭，不代表已完成全仓审计。
- 平台访问与会话恢复：[035 设计](design/035-平台访问与会话恢复能力设计.md) · [需求](prd/035-平台访问与会话恢复能力需求.md) · [计划](plans/035-平台访问与会话恢复能力计划.md) · [验收](acceptance/035-平台访问与会话恢复能力验收.md)。用户已批准开始实施；平台 G1–G3/G5 尚未通过，首批代码质量修复不等同换机与全平台成功。GitHub 依据见 [020 调研](research/020-平台会话生命周期与跨机器恢复调研.md)。
- 邮箱验证注册：[设计](design/033-邮箱验证注册设计.md) · [需求](prd/033-邮箱验证注册需求.md) · [计划](plans/033-邮箱验证注册计划.md) · [验收](acceptance/033-邮箱验证注册验收.md)。
- [业务增强与外部服务整合调研](research/019-业务增强与外部服务整合调研.md)：2026-09-08 业务闭环增强顺序、10 个 GitHub 候选的接入取舍、维护/许可证证据与最小验收。
- [业务逻辑评审与 ToC 最小上线能力](research/018-业务逻辑评审与ToC最小上线能力.md)：2026-09-08 Server/Web/App 当前实现评审、已复现问题、可用性与分阶段最小上线缺口。
- [个人部署重启与换机](operations/008-个人部署重启与换机手册.md)：会话文件、持久配置、受控平台选择和迁移边界。

- [前端视觉系统](design/frontend-visual-system.md)：Next.js、Vercel/Geist 无边框视觉、响应式和可访问性规范。
- [媒体解析策略](design/media-source-strategy.md)：解析责任链、错误优先级、封面认证交付与部署方 Provider Secret 生命周期。
- [Provider 接入架构重构调研](research/008-Provider接入架构重构调研.md)：yt-dlp 官方扩展边界、现有耦合和声明式接入结论。
- [微信与腾讯授权媒体调研](research/014-微信视频号与腾讯视频授权媒体下载调研.md)：公众号文章原生视频、视频号 GitHub 方案、腾讯消费站权益与腾讯云 VOD 官方边界。
- [微信视频号公开分享链接服务端解析调研](research/015-微信视频号公开分享链接服务端解析调研.md)：匿名公开媒体边界、消费端私有会话方案的否决结论与官方能力缺口。
- [LangChain 与 DeepSeek 视觉分析服务调研](research/016-LangChain与DeepSeek视觉分析服务调研.md)：默认 Codex、Web 可选 DeepSeek、服务端顺序截图和依赖安全边界。
- [Agent 视频 Skill 与成片分析能力调研](research/017-Agent视频Skill与成片分析能力调研.md)：55 项 AI 成片产线信号、专项分析 Skill 取舍与文档基础解析结论。
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
| 006 | 准入与部署修复；目标环境上线验收待完成 | [Design](design/006-上线产品能力补全设计.md) | [PRD](prd/006-上线产品能力补全需求.md) | [Plan](plans/006-上线产品能力补全计划.md) | [Acceptance](acceptance/006-上线产品能力补全验收.md) |
| 010 | Codex 与 Claude CLI 视频分析 | [Design](design/010-Codex与Claude CLI视频分析设计.md) | [PRD](prd/010-Codex与Claude CLI视频分析需求.md) | [Plan](plans/010-Codex与Claude CLI视频分析迁移计划.md) | [Acceptance](acceptance/010-Codex与Claude CLI视频分析验收.md) |
| 017 | 其他短视频平台分阶段接入 | [Design](design/017-其他短视频平台分阶段接入设计.md) | [PRD](prd/017-其他短视频平台分阶段接入需求.md) | [Plan](plans/017-其他短视频平台分阶段接入计划.md) | [Acceptance](acceptance/017-其他短视频平台分阶段接入验收.md) |
| 019 | 用户设备 Edge Agent 与媒体制品导入 | [Design](design/019-用户设备EdgeAgent与媒体制品导入设计.md) | [PRD](prd/019-用户设备EdgeAgent与媒体制品导入需求.md) | [Plan](plans/019-用户设备EdgeAgent与媒体制品导入计划.md) | [Acceptance](acceptance/019-用户设备EdgeAgent与媒体制品导入验收.md) |
| 022 | 跨平台 AI 分析 Agent 与模型 Provider 配置 | [Design](design/022-跨平台AI分析Agent与模型Provider配置设计.md) | [PRD](prd/022-跨平台AI分析Agent与模型Provider配置需求.md) | [Plan](plans/022-跨平台AI分析Agent与模型Provider配置计划.md) | [Acceptance](acceptance/022-跨平台AI分析Agent与模型Provider配置验收.md) |
| 023 | 本地内容上传与剧本分析 | [Design](design/023-本地内容上传与剧本分析设计.md) | [PRD](prd/023-本地内容上传与剧本分析需求.md) | [Plan](plans/023-本地内容上传与剧本分析计划.md) | [Acceptance](acceptance/023-本地内容上传与剧本分析验收.md) |
| 024 | 微信公众号文章、视频号与腾讯授权媒体接入 | [Design](design/024-微信视频号与腾讯视频授权媒体接入设计.md) | [PRD](prd/024-微信视频号与腾讯视频授权媒体接入需求.md) | [Plan](plans/024-微信视频号与腾讯视频授权媒体接入计划.md) | [Acceptance](acceptance/024-微信视频号与腾讯视频授权媒体接入验收.md) |
| 025 | 微信视频号公开分享链接下载 | [Design](design/025-微信视频号公开分享链接下载设计.md) | [PRD](prd/025-微信视频号公开分享链接下载需求.md) | [Plan](plans/025-微信视频号公开分享链接下载计划.md) | [Acceptance](acceptance/025-微信视频号公开分享链接下载验收.md) |
| 026 | Flutter 原生认证契约 | [Design](design/026-Flutter原生认证契约设计.md) | [PRD](prd/026-Flutter原生认证契约需求.md) | [Plan](plans/026-Flutter原生认证契约计划.md) | [Acceptance](acceptance/026-Flutter原生认证契约验收.md) |
| 027 | 开场钩子审查 Skill | [Design](design/archive/027-开场钩子审查Skill设计.md) | [PRD](prd/archive/027-开场钩子审查Skill需求.md) | [Plan](plans/archive/027-开场钩子审查Skill计划.md) | [Acceptance](acceptance/archive/027-开场钩子审查Skill验收.md) |
| 028 | AI 分析 Skill 与文档基础解析增强 | [Design](design/028-AI分析Skill与文档基础解析增强设计.md) | [PRD](prd/028-AI分析Skill与文档基础解析增强需求.md) | [Plan](plans/028-AI分析Skill与文档基础解析增强计划.md) | [Acceptance](acceptance/028-AI分析Skill与文档基础解析增强验收.md) |
| 029 | 付费内容识别与授权获取 | [Design](design/029-付费内容识别与授权获取设计.md) | [PRD](prd/029-付费内容识别与授权获取需求.md) | [Plan](plans/029-付费内容识别与授权获取计划.md) | [Acceptance](acceptance/029-付费内容识别与授权获取验收.md) |
| 030 | 运行故障隔离与恢复 | [Design](design/030-运行故障隔离与恢复设计.md) | [PRD](prd/030-运行故障隔离与恢复需求.md) | [Plan](plans/030-运行故障隔离与恢复计划.md) | [Acceptance](acceptance/030-运行故障隔离与恢复验收.md) |
| 031 | 个人部署重启与换机；文件来源已实现，实机待验收 | [Design](design/031-Linux无人值守运行设计.md) | [PRD](prd/031-Linux无人值守运行需求.md) | [Plan](plans/031-Linux无人值守运行计划.md) | [Acceptance](acceptance/031-Linux无人值守运行验收.md) |
| 032 | 腾讯与优酷个人下载；代码已接入，VIP 实测待完成 | [Design](design/032-腾讯视频与优酷个人下载设计.md) | [PRD](prd/032-腾讯视频与优酷个人下载需求.md) | [Plan](plans/032-腾讯视频与优酷个人下载计划.md) | [Acceptance](acceptance/032-腾讯视频与优酷个人下载验收.md) |
| 035 | 平台访问策略、会话生命周期与跨机器恢复；首批基础修复已实施，平台可行性待验证 | [Design](design/035-平台访问与会话恢复能力设计.md) | [PRD](prd/035-平台访问与会话恢复能力需求.md) | [Plan](plans/035-平台访问与会话恢复能力计划.md) | [Acceptance](acceptance/035-平台访问与会话恢复能力验收.md) |
| 036 | 内容创作与平台发布；研究与设计完成，待实施 | [Design](design/036-内容创作与平台发布设计.md) | [PRD](prd/036-内容创作与平台发布需求.md) | [Plan](plans/036-内容创作与平台发布计划.md) | [Acceptance](acceptance/036-内容创作与平台发布验收.md) |

本次全业务一致性：[034 设计](design/034-App与Web业务一致性设计.md) · [需求](prd/034-App与Web业务一致性需求.md) · [计划](plans/034-App与Web业务一致性计划.md) · [验收](acceptance/034-App与Web业务一致性验收.md)。
