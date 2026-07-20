# Plan 文档

本目录存放执行计划类文档。

## 当前文档

- [001 服务基座与运行配置计划](001-服务基座与运行配置计划.md)：Implemented；Acceptance 001 Blocked。
- [003 异步任务与数据持久化计划](003-异步任务与数据持久化计划.md)：Implemented；Acceptance 003 Blocked。
- [002 视频解析、下载与文件交付计划](002-视频解析下载与文件交付计划.md)：Implemented；Acceptance 002 Blocked。
- [004 API、会话与异常契约计划](004-API会话与异常契约计划.md)：Implemented；Acceptance 004 Blocked。

执行已按 `001 → 003 → 002 → 004` 完成并合并到 `main`。Plan 在对应 Acceptance 变为 Accepted 前继续留在活动目录；此处的 Implemented 只表示代码任务完成，不代表强验收通过。

任一上游变化、编号缺少任务/验证/证据、真实依赖不可用或全量命令失败时，对应 Plan 立即失去 Ready 或在执行时标记 `blocked/failed`。

## 阶段验收门禁

每个 Plan 必须在实现前关联一份 `Defined` Acceptance。Acceptance 预先冻结阶段前置条件、逐任务验收、DAC/AC、命令和证据要求；Plan 为 Ready 不等于可以开始，只有对应 Acceptance 的开始门禁满足且用户明确授权后才能实现。当前任务验收未 `passed` 前不得开始下一任务。

## 适合放入

1. 阶段计划与任务拆解。
2. 任务编排和归档路线。
3. 里程碑、排期和交付顺序。
4. 风险、依赖和后续事项。

## 不适合放入

1. 产品需求原文。
2. 详细技术设计。
3. 验收报告或测试记录。
4. 仅服务当前执行的 todo 列表、临时进展记录或过程流水账。

## 命名建议

使用 `序号-主题-计划.md`，例如 `001-docs目录治理计划.md`。
