# video-server 文档

本目录维护万能视频下载器 MVP 服务端的设计基线、需求、执行计划和验收证据。MVP 实现已合并到 `main`；未通过的强验收项继续在活动 Acceptance 中跟踪。

## 当前文档

- [Design 索引](design/README.md)：4 份已实现基线，已归档到 `design/archive/`。
- [PRD 索引](prd/README.md)：4 份已实现需求，已归档到 `prd/archive/`。
- [Plan 索引](plans/README.md)：4 份均已实施；因 Acceptance 为 Blocked，暂留活动目录。
- [Acceptance 索引](acceptance/README.md)：4 份均已执行并保持 Blocked，继续补齐真实环境证据。

## 唯一交付链

`Design → PRD → Plan → Acceptance`

1. `design/`：先明确服务目标、用户、能力边界、非目标、技术架构、API、数据、安全、风险、回滚及不可豁免的执行验收标准与证据。
2. `prd/`：只基于 accepted Design 固化用户价值、范围、业务规则与可衡量产品验收，不得降低 Design 标准。
3. `plans/`：只基于 accepted Design 与 PRD 拆分实现、测试、依赖和交付顺序。
4. `acceptance/`：在 Plan 实现前冻结阶段前置门禁、逐任务标准、DAC/AC、命令和证据要求；实现后原地填写证据与结论。
5. `operations/`：只承载验收后的发布、部署、回滚与运行手册，不是核心交付阶段。

## 当前门禁

- 每个阶段开始前必须已有对应的 `Defined` Acceptance；前置门禁不满足或未获得明确实现授权时不得创建业务代码。
- 当前范围以 `design/archive/` 与 `prd/archive/` 的 001–004 基线为准；AI、字幕、播放列表、批量、账号、历史和私有媒体均不在 MVP。
- 当前实现已进入 `main`；新功能必须创建新的 Design/PRD/Plan/Acceptance，不得直接改写归档基线。
- Acceptance 在实现前冻结标准；Plan 完成后只补充命令、证据和 `passed/failed/blocked` 结论。
- 不在 `docs/` 保存 todo、临时任务、进度记录、排查流水、会议记录、日记或重复模板。
- 各分类的格式与收录规则见对应目录的 `README.md`。
