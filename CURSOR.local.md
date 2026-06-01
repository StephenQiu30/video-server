# CURSOR.local.md

本文件用于记录放在具体项目中的局部规范性配置，与 `CURSOR.md` 中的全局协作规则进行区分。

## 使用边界

1. `CURSOR.md` 存放长期稳定的 Cursor 全局规则、角色协作原则和交付格式。
2. `CURSOR.local.md` 存放当前项目特有的规范、路径、命令、环境约束和临时协作约定。
3. 当局部规范与全局规则冲突时，应优先确认项目上下文，并以更具体、更贴近当前项目的规则为准。

## 当前项目规范

1. 本项目内的角色配置放在 `.cursor/agents/` 目录。
2. 本项目内的可复用流程放在 `.cursor/skills/` 目录。
3. Cursor 入口与 Codex 入口、Claude 入口并存；不要删除 `AGENTS.md`、`CLAUDE.md`、`.codex/`、`.claude/` 或 `.cursor/rules/`。
4. 本项目的统一验证入口为 `npm test`，其中包含仓库结构检查、Shell 脚本语法检查、生产环境示例校验和 API 测试。
