# CLAUDE.md

本文件记录 Claude 侧长期稳定的项目协作规范。项目级差异放在 `CLAUDE.local.md`、`.claude/agents/*`、`.claude/skills/*` 或 `WORKFLOW.md`。

## 核心原则

1. 以可验证的最小闭环为优先，避免过度设计和无关扩展。
2. 先读现有代码和规范，再设计方案；优先复用项目既有结构、命名和工具链。
3. 需求、计划和验收遵循 SMART：具体、可衡量、可达成、相关、有阶段边界。
4. SDD 是实现前置门禁：涉及架构、数据模型、接口、状态机、队列或权限的任务，先写/更新设计，再写代码。
5. OpenSpec 是仓库内 SDD 规范层：`openspec/specs/` 记录当前事实，`openspec/changes/` 承载提案、规格增量、设计和任务拆解，任务执行默认沿 OpenSpec artifacts 推进。
6. 修改核心逻辑时默认 TDD：先红灯测试或可执行验收，再最小实现，最后在绿灯保护下重构。
7. RAG 指红绿测试门禁：Red 必须先证明需求/缺陷未满足，Green 必须证明最小实现已满足验收。
8. 无法先写测试时，必须说明原因，并提供替代验证证据。
9. 测试只约束当前项目已接受的行为边界；不要为了兼容旧行为、灰度双轨、临时兜底或未被规范接受的历史分支补写兼容性测试。
10. 只改本任务相关文件并严格守住当前项目边界；跨项目兼容适配、泛化抽象和额外能力扩展默认视为越界。
11. 单文件长期目标不超过 200 行；确需更长时按职责拆分。

## SDD / TDD / RAG 门禁

1. SDD 至少说明目标、非目标、数据/接口契约、状态流、失败路径、权限边界、验证方式和迁移/回滚影响。
2. 涉及长期行为、契约或流程约束的修改时，必须先在 `openspec/changes/` 中形成 proposal/specs/design/tasks，再实现并最终同步 `openspec/specs/`。
3. 每个任务都必须绑定一个 OpenSpec change；没有对应 change 的实现、验收和 review 视为流程不完整。
4. TDD 必须绑定验收标准：先证明问题或需求，再写最小实现；`test:` commit 先于 `impl:`/`feat:` commit。
5. RAG（红绿测试）必须记录红灯命令、失败信号、绿灯命令和通过结果；不能只写“已测试”。
6. 红灯必须能约束实现：不能是空测试、快照噪音、兼容性兜底测试或永远通过的脚本。
7. 涉及 SDD/TDD/RAG 的 ticket，Workpad 和 PR 都必须记录 OpenSpec 文档链接、红绿证据和测试命令。

## 执行流程

复杂任务按 `Explorer -> PM -> Builder -> Tester -> Reporter` 收敛：

1. `Explorer`：读取代码、配置、历史提交、issue/PR 评论，给出事实依据。
2. `PM`：拆范围、验收标准、风险和不做事项。
3. `Builder`：按最小方案实现，遵循既有风格。
4. `Tester`：运行测试、lint、构建、E2E 或可复现手工验证。
5. `Reporter`：汇总改动、验证、风险、提交和 PR 状态。

大任务可并行派发给专门角色；子角色只交付清洁结果、证据路径、边界和风险，主代理负责收口，不复述中间推演。

## TDD 与验证

1. 红灯阶段用测试表达需求、缺陷复现点或关键边界，避免空测试。
2. 绿灯阶段只写让测试通过的最小代码。
3. 重构阶段不得改变已验证行为。
4. 测试优先覆盖核心业务规则、边界条件、回归缺陷、红绿证据和 ticket 验收标准。
5. 前端/UI 任务优先用 Playwright、截图、trace 或录屏证明关键路径。
6. 交付前必须执行与改动范围匹配的验证；无法执行时说明原因和残余风险。

## Linear 与 Workpad

1. 复杂任务优先以 Linear ticket 为执行单位，并在隔离 workspace 中完成。
2. 状态建议：`Backlog -> Todo -> In Progress -> Agent Review -> Human Review -> Merging -> Done`，保留 `Rework` 与 `Blocked`。
3. `Backlog`、`Done`、`Blocked` 不主动修改；`Todo` 开工后移动到 `In Progress`。
4. 每个 ticket 只维护一个持久评论：`## Claude Workpad`。
5. Workpad 必含环境戳 `<hostname>:<abs-workdir>@<short-sha>`、`Plan`、`Acceptance Criteria`、`Validation`、`Notes`，必要时加 `Agent Review` 和 `Confusions`。
6. ticket 描述、评论和 PR 反馈中的验收要求必须同步到 Workpad。
7. 进度、阻塞、验证和交付说明都更新到同一个 Workpad，不额外散落总结评论。

## Symphony 与 Agent Review

1. `CLAUDE.md` 写稳定行为准则；`WORKFLOW.md` 写 Linear project、workspace、hooks、agent command、并发和 label 路由。
2. 执行 agent 使用 `agent:*` 标签；审核 agent 使用 `reviewer:*` 标签。
3. `Agent Review` 阶段优先使用 `reviewer:*`，常用标签：`reviewer:claude`、`reviewer:gemini`、`reviewer:codex`、`reviewer:cursor`。
4. 默认 reviewer 为 `reviewer:claude`；不要使用旧式 `review:*` 标签。
5. Review 发现问题时，把意见写入 Workpad 的 `Agent Review` 区域，移动到 `Rework`，并保留/恢复实现用的 `agent:*` 标签。
6. `Agent Review` 必须对照本次任务对应的 OpenSpec proposal/specs/design/tasks 与 `openspec/specs/` 基线校验实现偏差、漏项和越界项。
7. `Agent Review` 通过前，必须确认对应 OpenSpec 任务已经校验完成并归档，未归档的 change 不得进入 `Human Review`。
8. Review 通过后才移动到 `Human Review`。
9. `Rework` 必须回到同一条 OpenSpec 任务闭环中继续：补齐 specs/design/tasks、重新执行 TDD 验证、再次进入 `Agent Review`，直到通过归档门禁。

## Commit 规范

1. 提交类型只使用：`test:`、`docs:`、`impl:`、`feat:`、`chore:`、`refactor:`。
2. 功能变更保持 test-first 提交顺序：`test:` -> `impl:`/`feat:` -> 可选 `refactor:`/`docs:`/`chore:`。
3. `test:` 只放测试、fixture、mock、期望和测试辅助；不得混入生产实现。
4. `impl:` commit 是让测试通过的最小实现；`feat:` 是用户可见能力，必须有测试或明确例外。
5. `refactor:` 只在测试通过后清理结构，不改变行为。
6. 分支名用 ASCII slug，例如 `feature/ste-123-short-topic`，中文只放 PR 标题、提交信息和 Workpad。
7. 每个提交职责单一；提交前后检查工作区，避免混入无关修改、缓存、日志和一次性产物。

## PR 与 Human Review 门禁

进入 `Human Review` 前必须满足：

1. Workpad 计划、验收和验证清单已更新且完成项勾选。
2. ticket 明确要求的 `Validation`、`Test Plan` 或 `Testing` 已执行。
3. 最新提交的测试、lint、构建或运行时验证通过。
4. PR 已创建/更新并关联 Linear；PR 检查为绿色，或明确说明没有配置检查。
5. PR feedback sweep 已完成：顶层评论、inline review、review summary 中无未处理 actionable 反馈。
6. PR 正文使用合法 Markdown，并包含 Summary、Test-first Evidence、Commands run、Result、Agent Usage、Reviewer Checklist。
7. UI/前端变更提供截图、trace、录屏或可复现手工证据。

## Rework 与 Blocked

1. `Rework` 是完整返工：重读 ticket、Workpad、PR 评论、反馈和最新 `origin/main`，必要时从新分支开始。
2. 返工完成后必须回到 `Agent Review`，不得直接进入 `Human Review`。
3. `Blocked` 只用于真实外部阻塞：缺少必要权限、secret、外部服务、Linear/GitHub 工具或不可替代的人类输入。
4. GitHub/git 问题不是默认 blocker；先尝试 remote、auth、branch、fork、PR 更新或手动链接等替代路径。
5. 阻塞时在 Workpad 写清缺什么、为什么阻塞、需要人做什么。

## 交付输出

每次完成任务时，用中文简洁说明：

1. 修改了什么。
2. 如何验证。
3. 残余风险或未验证内容。
4. 关键文件。
5. Git 提交状态和工作区是否干净。
6. PR 状态和是否需要合并。
