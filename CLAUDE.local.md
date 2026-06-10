# CLAUDE.local.md

本文件用于记录放在具体项目中的局部规范性配置，与 `CLAUDE.md` 中的全局协作规则进行区分。

## 使用边界

1. `CLAUDE.md` 存放长期稳定的 Claude 全局规则、角色协作原则和交付格式。
2. `CLAUDE.local.md` 存放当前项目特有的规范、路径、命令、环境约束和临时协作约定。
3. 当局部规范与全局规则冲突时，应优先确认项目上下文，并以更具体、更贴近当前项目的规则为准。

## 当前项目规范

1. 本项目内的角色配置放在 `.claude/agents/` 目录。
2. 本项目内的可复用流程放在 `.claude/skills/` 目录。
3. 本项目的统一验证入口为 `npm test`，其中包含仓库结构检查、Shell 脚本语法检查、生产环境示例校验和 API 测试。
4. 本项目采用 OpenSpec 作为 SDD 规范层；`openspec/specs/` 记录当前事实，`openspec/changes/` 承载增量变更。
5. Symphony workspace 创建后需安装 Node 与 Python 依赖；详见 `WORKFLOW.md` 的 `after_create` hooks。
