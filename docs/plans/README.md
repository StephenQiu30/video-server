---
layer: docs-readme
doc_no: "PLANS-INDEX"
audience:
  - Dev
  - PM
purpose: "说明后端文档中的计划类资料放置规则。"
canonical_path: "docs/plans/README.md"
status: "ready"
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/04-执行计划/*"
outputs:
  - "任务拆解、路线图、里程碑"
---

# 后端计划文档目录

`docs/plans/` 用于沉淀后端主仓库层面的实施计划与拆解，不用于一次性排查记录。

- 长周期计划：按阶段维护，如 `01-阶段执行计划.md`、`04-落地页重构实施计划.md`。
- 里程碑微拆分：按执行步骤拆分到最小任务，用于分解 issue 与验收。
- 与 `issues` 对齐：每个计划文档中的任务应映射到 issue 的最小执行单元。

更新策略

- 每次大改后优先补充本目录中的计划变更，避免让测试记录与临时决议混入。
- 计划文档应说明“已完成/进行中/阻塞”状态和验收门槛。
- 当双仓库迁移收口完成后，补充“旧 `apps/web` 收口策略”到对应执行计划中。

本目录下新增文档优先写明与 `video-server` API 契约的依赖关系，便于前后端仓库联调。 
