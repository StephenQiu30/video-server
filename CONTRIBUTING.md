# Contributing

感谢你愿意改进 `video-server`。

## 贡献范围

1. 修正 `AGENTS.md`、`AGENTS.local.md` 与 `WORKFLOW.md` 中的项目规范。
2. 优化 `.codex/agents/` 角色或 `.codex/skills/` 核心流程。
3. 按 `Design → PRD → Plan → Acceptance` 更新正式文档。
4. 在 Plan ready 后交付其明确授权的最小实现与验证。

## 贡献原则

1. 遵循 MVP，不引入当前没有使用场景的复杂流程。
2. 保持 Design、PRD、Plan、Acceptance、TDD 与实际改动一致。
3. 每个 Plan 实现前先将对应 Acceptance 定义为 `Defined`；实现后只填写证据与结论，标准变化必须先返回上游文档。
4. README 与文档只描述仓库真实存在的结构和能力。
5. 单个文件长期目标不超过 200 行；确需更长时按职责拆分。

## 提交流程

1. 提交前检查真实 Git 根、分支、状态与改动范围。
2. 功能改动遵循 `test:` → `impl:`/`feat:` → 可选 `refactor:`/`docs:`/`chore:`。
3. `test:` 只包含测试、fixture、mock、期望结果和测试辅助工具；实现提交只包含最小实现。
4. 不提交 secret、缓存、日志、构建产物、临时文件或过程记录。
5. 使用中文提交信息、PR 标题与描述，并填写 Test-first Evidence、验证命令、结果和 Agent 使用情况。
6. PR 合并前为准确落地提交创建并推送 annotated pre-merge tag。
