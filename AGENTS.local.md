# AGENTS.local.md

本文件记录 `video-server` 的项目级边界；长期稳定规则以 `AGENTS.md` 为准。

## 当前项目规范

1. 本仓库只负责服务端；不得修改相邻的 `video-web` 或其他仓库。
2. 当前没有已接受的产品或技术设计，不得假设服务范围、功能、技术栈、API、数据库或部署形态。
3. 唯一交付链是 `Design → PRD → Plan → Acceptance`；下一轮从 Design 开始，禁止跳级或倒序补文档。
4. Design accepted 前不创建 PRD 或 Plan；Design 与 PRD accepted、Plan ready 且用户明确要求实现前，不得创建业务源码、依赖、测试、migration、schema、fixture 或业务运行配置。
5. 项目角色放在 `.codex/agents/`，可复用流程放在 `.codex/skills/`。
6. 不维护 `.planning`、日记、临时进度文件、占位功能或重复治理目录。
