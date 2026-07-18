# video-server 文档

本目录已完成 MVP 的功能拆分：Design 已确认，PRD 已可规划，Plan 已就绪；业务实现和 Acceptance 尚未开始。

## 当前文档

- [Design 索引](design/README.md)：5 份，状态为 Accepted。
- [PRD 索引](prd/README.md)：5 份，状态为 Accepted for Planning。
- [Plan 索引](plans/README.md)：5 份，状态为 Ready，尚未开始实现。
- `acceptance/`：仅保留分类说明，暂无验收文档。

## 唯一交付链

`Design → PRD → Plan → Acceptance`

1. `design/`：先明确服务目标、用户、能力边界、非目标、技术架构、API、数据、安全、风险、回滚及不可豁免的执行验收标准与证据。
2. `prd/`：只基于 accepted Design 固化用户价值、范围、业务规则与可衡量产品验收，不得降低 Design 标准。
3. `plans/`：只基于 accepted Design 与 PRD 拆分实现、测试、依赖和交付顺序。
4. `acceptance/`：逐项验证 Design、PRD 与 Plan，只记录方法、证据和结论，不在验收阶段修改标准。
5. `operations/`：只承载验收后的发布、部署、回滚与运行手册，不是核心交付阶段。

## 当前门禁

- 不沿用已清除旧文档中的结论；当前范围只以本轮 Design、PRD 和 Plan 为准。
- 未收到明确实现指令前，不执行 Ready Plan，不创建业务代码。
- Plan 完成实现和验证前，不创建 Acceptance。
- 不在 `docs/` 保存 todo、临时任务、进度记录、排查流水、会议记录、日记或重复模板。
- 各分类的格式与收录规则见对应目录的 `README.md`。
