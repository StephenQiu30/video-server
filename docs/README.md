# video-server 文档

本目录是重新设计后的空文档基线。当前没有产品级 Design、PRD、Plan 或 Acceptance。

## 唯一交付链

`Design → PRD → Plan → Acceptance`

1. `design/`：先明确服务目标、用户、能力边界、非目标、技术架构、API、数据、安全、风险与回滚。
2. `prd/`：只基于 accepted Design 固化用户价值、范围、业务规则与可衡量验收标准。
3. `plans/`：只基于 accepted Design 与 PRD 拆分实现、测试、依赖和交付顺序。
4. `acceptance/`：逐项验证 Design、PRD 与 Plan，记录方法、证据、结果和残余风险。
5. `operations/`：只承载验收后的发布、部署、回滚与运行手册，不是核心交付阶段。

## 当前门禁

- 所有产品事实均待重新设计，不沿用已清除文档中的结论。
- Design accepted 前，不创建下游文档或业务实现。
- 不在 `docs/` 保存 todo、临时任务、进度记录、排查流水、会议记录、日记或重复模板。
- 各分类的格式与收录规则见对应目录的 `README.md`。
