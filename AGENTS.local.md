# AGENTS.local.md

本文件记录 `video-server` 在全面重置后的局部边界，与 `AGENTS.md` 的通用 Codex 规范配合使用。

## 空仓边界

1. 当前没有已批准的产品范围、技术栈、架构、接口、数据模型或运行命令。
2. 当前没有产品源码、测试、部署或运行时实现；不要把 Git 历史和已删除文件解释为现行需求。
3. 不得为了兼容旧实现恢复历史目录、依赖、配置、接口或文档。

## 新设计门禁

1. 新工作按 `PRD -> Design -> Plan -> Acceptance -> Implementation` 建立新的事实链。
2. PRD 和 Design 未批准前，不选择技术栈，不创建产品脚手架，不写产品实现。
3. Implementation 阶段遵循 `AGENTS.md` 的 SDD、TDD、RAG 与验证要求。

## Codex 资产

1. Subagent 位于 `.codex/agents/`。
2. Skill 位于 `.codex/skills/`。
3. 编排规则位于 `WORKFLOW.md`。
4. 当前空仓没有产品验证命令；新的验证方式必须由新设计明确引入。
