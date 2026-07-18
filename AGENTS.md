# AGENTS.md

本文件只记录 Codex 侧长期稳定的协作规则。项目级路径、命令和环境约束放在 `AGENTS.local.md`；Linear 编排、workspace、hooks 和运行时配置放在 `WORKFLOW.md`；角色与可复用操作分别放在 `.codex/agents/` 和 `.codex/skills/`。

## 核心原则

1. 以可验证的最小闭环为先，不做无关扩展、过度设计或跨项目兼容层。
2. 先确认真实 Git 根目录、分支、工作区状态和项目规范，再读取代码与历史；只修改任务范围内的文件。
3. 复用现有架构、命名和工具链。发现额外需求时另建任务，不顺手扩大当前范围。
4. 需求与验收遵循 SMART；复杂行为遵循 SDD；核心逻辑默认使用 TDD 的 Red → Green → Refactor。
5. 测试只保护当前已接受的契约，不为未被规范接受的旧行为、临时兜底或灰度双轨补兼容测试。
6. 无法先写测试时，先说明原因并定义最接近的可执行验收，再实现。
7. 单文件长期目标不超过 200 行；确需更长时按职责拆分。

## 唯一交付流程

所有需要正式文档的功能按以下顺序推进，禁止跳级或倒序补文档：

`Design → PRD → Plan → Acceptance`

1. `Design`：先明确问题、约束、现状、目标架构、接口/数据契约、状态流、失败路径、权限、迁移和回滚；结论写入 `docs/design/`。
2. `PRD`：基于已接受的 Design 固化用户价值、范围、非目标、用户故事、业务规则和可衡量验收标准；写入 `docs/prd/`。
3. `Plan`：基于 Design 与 PRD 拆分实现、测试、依赖、风险和交付顺序；写入 `docs/plans/`。实现和验证只能在 Plan 可执行后开始。
4. `Acceptance`：按 Design、PRD、Plan 逐项验证，记录命令、结果、证据、残余风险和结论；写入 `docs/acceptance/`。

每一阶段必须声明输入、输出、状态和下游文档。上游变化时先更新受影响文档，再继续下游。`docs/operations/` 只承载验收后的发布、部署、回滚和运维说明，不增加核心流程阶段。

## 执行与验证

1. 开始前定位治理本任务的 Design、PRD、Plan 和 Acceptance；缺失的上游文档按流程补齐。
2. 先复现当前行为或失败信号，并把证据与验收标准绑定。
3. 功能或缺陷修复先提交可失败的 `test:` 约束，再用最小 `impl:`/`feat:` 使其通过，最后按需 `refactor:`。
4. Red 必须证明需求尚未满足；Green 必须证明最小实现已满足验收。记录具体命令和结果，不写笼统的“已测试”。
5. 验证范围与风险匹配：运行目标测试、lint、构建、集成测试或可复现手工检查。
6. UI 变更使用项目已有的启动与浏览器验证工具检查关键路径，并保存截图、页面状态或复现步骤。
7. 实现后逐项回填 Acceptance；失败、阻塞或无证据的条目不能判定通过。

## Linear 与 Workpad

1. 复杂任务以 Linear ticket 和隔离 workspace 为执行单位；状态流由 `WORKFLOW.md` 定义。
2. 每个 ticket 只维护一个 `## Codex Workpad`，不散落额外进度或完成评论。
3. Workpad 至少包含环境戳 `<hostname>:<abs-workdir>@<short-sha>`、Execution Documents、Plan、Acceptance Criteria、Validation 和 Notes。
4. ticket 描述、评论、PR 反馈和正式文档中的验收要求都要同步到同一 Workpad。
5. `Blocked` 只用于缺少必要权限、secret、外部服务、工具或不可替代的人类决策；普通实现困难不是阻塞。
6. `Agent Review` 必须从 Design、PRD、Plan、ticket 和 Workpad 导出编号清单，并为每项记录 `passed`、`failed` 或 `blocked` 及证据。
7. 任一条未通过或缺少证据时进入 `Rework`；全部通过后才进入 `Human Review`。

## 角色边界

复杂任务按 `Explorer → PM → Builder → Tester → Reporter` 收敛：

- `Explorer`：核验代码、配置、历史、issue 和 PR，提供事实依据。
- `PM`：控制范围、验收、风险和非目标，维护正式文档与 Workpad。
- `Builder`：按 Plan 完成最小实现，不扩大契约。
- `Tester`：独立执行测试、构建、运行时或 UI 验证，并检查 Acceptance。
- `Reporter`：汇总改动、证据、风险、Git 和 PR 状态。

仅在任务可独立拆分且主代理能够统一验收时并行；子角色交付结果、证据、边界和风险，主代理负责最终收口。

## Git 与 PR

1. 提交类型只使用 `test:`、`docs:`、`impl:`、`feat:`、`chore:`、`refactor:`，每个提交职责单一。
2. 功能变更保持 `test:` → `impl:`/`feat:` → 可选 `refactor:`/`docs:`/`chore:` 的顺序。
3. 新 PR 分支必须匹配 `feature/[a-z][a-z0-9_]*`；slug 描述真实能力，不含 ticket ID、中文、连字符或其他前缀。
4. 提交前后检查 diff 与工作区，排除无关修改、secret、缓存、日志、构建产物和一次性文件。
5. PR 正文遵循仓库模板，至少说明 Summary、Test-first Evidence、Commands、Result、Agent Usage 和 Reviewer Checklist。
6. 进入 `Human Review` 前，目标验证与 PR feedback sweep 必须完成，PR 检查为绿色或明确说明未配置检查。
7. 人工批准进入 `Merging` 后，为准确落地提交创建并推送 annotated pre-merge tag，再执行 `.codex/skills/land/SKILL.md`；不要直接调用 `gh pr merge`。
8. `Rework` 必须重读正式文档、ticket、Workpad、PR 反馈和最新 `origin/main`，完成后重新进入 `Agent Review`。

## 交付格式

每次完成任务时，用中文简洁说明：

1. 修改内容与关键文件。
2. 验证命令、结果和 Acceptance 结论。
3. 残余风险或未验证项。
4. Git 提交、工作区、PR 和合并状态。
