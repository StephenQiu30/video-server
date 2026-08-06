# AGENTS.md

本文件只记录长期稳定的协作与交付门禁。项目边界和当前阶段放在 `AGENTS.local.md`；Linear/Symphony 编排放在 `WORKFLOW.md`；角色与可复用操作放在 `.codex/agents/` 和 `.codex/skills/`；产品与技术事实只以 `docs/` 正式文档为准。

## 范围与事实来源

1. 开始前确认真实 Git 根目录、分支、远端、工作区状态和仓库内规范，只修改用户明确授权的仓库与文件。
2. 不从旧实现、已删除文档、聊天推测或相邻仓库继承产品事实；发现冲突时先停止并更新正式上游文档。
3. 以可验证的最小闭环为先，复用已接受的架构、命名和工具链，不顺手增加兼容层、泛化抽象或额外能力。
4. 不保存 `.planning`、日记、临时进度、排查流水、重复模板或一次性状态文件。
5. 单文件长期目标不超过 200 行；确需更长时按职责拆分。

## 唯一交付链

正式功能固定遵循：

`Design → PRD → Plan → Acceptance`

1. `Design`：定义目标与非目标、架构、接口/数据契约、状态流、失败路径、安全、迁移/回滚以及编号化 Design Acceptance Criteria（DAC）和证据要求。
2. `PRD`：基于 accepted Design 固化用户价值、范围、业务规则和编号化产品 Acceptance Criteria（AC），不得降低 DAC。
3. `Plan`：显式映射全部 DAC 与 AC，拆分 test-first 实现、依赖、验证命令和交付顺序；缺项或冲突时状态不得为 Ready。
4. `Acceptance`：在对应 Plan 实现前以 `Defined` 状态冻结阶段前置条件、逐任务验收、DAC/AC、命令和证据要求；实现后只在同一文档补充实际命令、退出码、证据和逐项结论，不新增、删除、合并或降级标准。
5. `Operations`：只承载 accepted 后的发布、部署、备份、恢复和回滚说明，不增加核心交付阶段。

上游变化时必须先更新所有受影响的下游文档。Design 与 PRD accepted、Plan Ready、对应 Acceptance 为 Defined 且用户明确要求实现前，不得创建业务实现。

## SDD、TDD 与验收

1. SDD 是实现前置门禁；复杂行为必须先由 Design、PRD、Plan 和对应的 Defined Acceptance 完整定义。
2. 核心逻辑默认 TDD：先写能证明需求尚未满足的 Red，再用最小实现得到 Green，最后在绿灯保护下 Refactor。
3. RAG 在本项目仅指 Red/Green 红绿测试门禁，不指检索增强生成；红绿证据必须记录具体命令、失败信号和通过结果。
4. 无法先写自动测试时，必须在实现前说明原因并定义最接近的可执行验收，不能用实现后的解释替代。
5. 验证范围与风险匹配，至少覆盖目标测试、全量测试、lint/格式、类型、构建、契约、真实依赖集成、失败路径、安全和必要端到端。
6. Mock、fixture、截图、静态检查或局部测试不能替代 Design 明确要求的真实环境证据。
7. 单项结论只允许 `passed`、`failed`、`blocked`；整体只有全部强制项 `passed` 且独立复核通过时才能 `accepted`。
8. 禁止“基本通过”“条件通过”或 `accepted_with_risk`。缺环境、Secret、外部服务或证据时必须 `blocked`；确需改标准时回到 Design/PRD，经用户确认后重新验证。
9. 具体阈值和证据矩阵以 `docs/design/README.md`、对应 Design 和 `docs/acceptance/README.md` 为唯一依据。

## 执行与审核

1. 复杂任务按 `Explorer → PM → Builder → Tester → Reporter` 收敛；主代理负责范围、证据和最终结论。
2. Linear 任务只维护一个 `## Codex Workpad`，同步 Execution Documents、Plan、Acceptance Criteria、Validation 和 Notes，不散落重复评论。
3. `Agent Review` 必须从 Design、PRD、Plan、ticket 和 Workpad 导出编号清单，逐项记录 `passed`、`failed` 或 `blocked` 及证据。
4. 任一项失败、阻塞或缺少证据时进入 Rework；全部通过后才进入 Human Review。
5. `Blocked` 只用于真实外部阻塞；普通实现困难不是阻塞。

## Git 与发布

1. 提交类型只使用 `test:`、`docs:`、`impl:`、`feat:`、`chore:`、`refactor:`，每个提交职责单一。
2. 行为变更保持 `test:` → `impl:`/`feat:` → 可选 `refactor:`/`docs:`/`chore:` 顺序；提交前后检查无关文件、Secret、缓存、日志和构建产物。
3. PR 分支使用 `feature/[a-z][a-z0-9_]*`，slug 描述真实能力，不含 ticket ID、中文、连字符或其他前缀。
4. 常规 PR、Human Review、Merging 与 pre-merge tag 流程以 `WORKFLOW.md` 和 `.codex/skills/land/SKILL.md` 为准。
5. 用户明确要求直接提交到 `main` 或不创建 PR 时，以该指令覆盖常规 PR 流程：先同步 `origin/main`，完成范围校验，创建单一职责提交，推送 `main`，再确认 `HEAD == origin/main`、工作区干净和 CI 结果。
6. 不强推、不改写远端、不静默暂存无关改动；推送失败时区分同步、认证和权限问题并按对应技能处理。

## 交付输出

完成任务时用中文简洁说明：改动与关键文件、验证命令和结果、Acceptance 结论、残余风险，以及分支、提交、推送、PR/CI 和工作区状态。
