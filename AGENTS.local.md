# AGENTS.local.md

本文件记录 `video-server` 的项目级边界；长期稳定规则以 `AGENTS.md` 为准。

## 当前项目规范

1. 本仓库只负责服务端；不得修改相邻的 `video-web` 或其他仓库。
2. 当前产品与技术事实只以 `docs/design/`、`docs/prd/` 和 `docs/plans/` 的本轮文档为准，不得恢复已清除旧设计或自行扩展范围。
3. 当前 5 份 Design 已 accepted、5 份 PRD 已 accepted for planning、5 份 Plan 已 ready；未收到用户明确实现指令前不得创建业务源码、依赖、测试、migration、schema、fixture 或业务运行配置。
4. 唯一交付链是 `Design → PRD → Plan → Acceptance`；执行必须满足 Design 中预先冻结的验收标准，任何下游文档不得降低标准或事后增加豁免。
5. 项目角色放在 `.codex/agents/`，可复用流程放在 `.codex/skills/`。
6. 不维护 `.planning`、日记、临时进度文件、占位功能或重复治理目录。
