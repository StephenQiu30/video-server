# AGENTS.local.md

本文件记录 `video-server` 的服务端局部边界，与 `AGENTS.md` 的通用 Codex 规范配合使用。

## 产品边界

1. 本仓库实现“授权视频下载与 AI 知识化工作台”的服务端能力。
2. “万能”指统一入口、能力探测和可扩展来源适配，不代表绕过登录、付费墙、下载禁用、地区限制或 DRM。
3. 只有同时满足用户拥有处理权、来源政策允许和技术措施未被绕过时，才允许进入下载链路。
4. 当前 Design、PRD、Plan 与 Acceptance 是新版本事实来源；不得从 Git 历史恢复旧产品实现或兼容层。

## 执行门禁

1. 新工作按 `Design -> PRD -> Plan -> Acceptance -> Implementation` 建立事实链。
2. 只有状态为 `ready` 的 Plan 可以进入实现；每次只推进一个依赖就绪的 Plan。
3. Acceptance 必须在实现前冻结方法和证据要求，实现后逐项记录 `passed`、`failed` 或 `blocked`。
4. Implementation 遵循 `AGENTS.md` 的 SDD、TDD、RAG 与验证要求，不得以占位实现冒充闭环。

## 当前实施范围

1. 当前唯一可推进候选是 `docs/plans/000-邮箱身份与持久化基础设施计划.md`；它必须先冻结并实现邮箱身份、PostgreSQL、可重建 Redis、MinIO 对象层和 SMTP 基础设施。
2. Plan 001 已退回 `review` 并等待 Plan 000 完成；此前完成的 Resolution PostgreSQL 原子创建与 rights history 只作为可复用的局部 Green，不代表 Plan 001 已通过。
3. Plan 001 仅覆盖 URL 策略校验、异步元数据解析、真实清晰度目录、任务查询与事件恢复；实际下载、媒体合流、AI 转录总结、思维导图和 PDF 分属后续 Plan，在其门禁通过前不得实现。
4. 所有业务 owner 必须是 PostgreSQL `users.id` 的 UUID；不得恢复安装令牌、共享主体或 Redis session 作为身份事实来源。

## Codex 资产

1. Subagent 位于 `.codex/agents/`。
2. Skill 位于 `.codex/skills/`。
3. 编排规则位于 `WORKFLOW.md`。
4. 验证命令必须随 Plan 001 实现进入仓库，并回填到对应 Acceptance。
