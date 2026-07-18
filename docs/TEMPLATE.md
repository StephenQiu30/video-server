---
layer: Design | PRD | Plan | Acceptance
status: draft
result: pending
version: "0.1.0"
canonical_path: docs/<category>/<file>.md
purpose: "本文档冻结的单一目标"
inputs: []
outputs: []
---

# 文档标题

## 1. 背景与事实

记录可验证现状、问题信号、用户输入和官方依据。不要把 Git 历史或被废弃实现当作现行需求。

## 2. 目标

列出具体、可衡量、有边界的目标，并引用上游需求或决策 ID。

## 3. 非目标

明确本轮不解决的事项，防止下游 Plan 隐式扩张。

## 4. 核心决策

按文档层级记录产品边界、技术权衡、需求编号、执行步骤或验收方法。

## 5. 契约与失败路径

说明数据、接口、状态、权限、安全、失败处理、幂等、迁移和回滚；不适用时写明原因。

## 6. 验证

列出可复现命令、场景、期望结果和证据形式。Acceptance 项只能记录 `passed`、`failed` 或 `blocked`。

## 7. 风险与待确认项

记录残余风险、外部依赖和必须由人确认的决定，不用模糊措辞掩盖不确定性。

## 8. 关联文档

- 输入：
- 输出：
- 下游：

## 9. 状态规则

- Design/PRD：`draft → review → accepted → superseded`。
- Plan：`draft → review → ready → in_progress → done` 或 `backlog`。
- Acceptance 文档：`draft → accepted`；执行结果单独使用 `pending/passed/failed/blocked`。

## 10. 变更记录

| 版本 | 日期 | 变更说明 |
| --- | --- | --- |
| 0.1.0 | YYYY-MM-DD | 初始化 |
