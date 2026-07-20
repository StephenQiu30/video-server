# video-server 文档

本目录定义万能视频下载器 MVP 的服务端需求、架构、API、数据表和未来源码目录。当前没有业务实现。

## 当前文档

- [Design 索引](design/README.md)：4 份，状态为 Accepted。
- [PRD 索引](prd/README.md)：4 份，状态为 Accepted for Planning。
- [Plan 索引](plans/README.md)：4 份，状态为 Ready；尚未授权实现。
- [Acceptance 索引](acceptance/README.md)：4 份阶段验收已预先定义，尚未执行。

## 唯一交付链

`Design → PRD → Plan → Acceptance`

1. `design/`：先明确服务目标、用户、能力边界、非目标、技术架构、API、数据、安全、风险、回滚及不可豁免的执行验收标准与证据。
2. `prd/`：只基于 accepted Design 固化用户价值、范围、业务规则与可衡量产品验收，不得降低 Design 标准。
3. `plans/`：只基于 accepted Design 与 PRD 拆分实现、测试、依赖和交付顺序。
4. `acceptance/`：在 Plan 实现前冻结阶段前置门禁、逐任务标准、DAC/AC、命令和证据要求；实现后原地填写证据与结论。
5. `operations/`：只承载验收后的发布、部署、回滚与运行手册，不是核心交付阶段。

## 当前门禁

- 每个阶段开始前必须已有对应的 `Defined` Acceptance；前置门禁不满足或未获得明确实现授权时不得创建业务代码。
- 当前范围只以本轮 Design 与 PRD 为准；AI、字幕、播放列表、批量、账号、历史和私有媒体均不在 MVP。
- Design/PRD 已确认且 Plan 已 Ready；用户未再次明确要求实现前，不创建业务代码。
- Acceptance 在实现前冻结标准；Plan 完成后只补充命令、证据和 `passed/failed/blocked` 结论。
- 不在 `docs/` 保存 todo、临时任务、进度记录、排查流水、会议记录、日记或重复模板。
- 各分类的格式与收录规则见对应目录的 `README.md`。
