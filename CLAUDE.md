# CLAUDE.md

本文件用于存放项目开发过程中的规范性要求。

## 项目开发原则

1. 项目开发遵循 MVP 原则，以最小可用功能闭环为优先，不对功能、架构、流程或文档进行过度设计。
2. 单个文件应保持清晰、可维护，原则上不要超过 200-500 行；当文件持续膨胀时，应按职责拆分为更小的模块。
3. 项目开发遵循 TDD 思想，新增或修改功能时优先使用红绿测试流程：先编写失败测试，再实现最小代码使测试通过，最后在测试保护下进行必要重构。
4. 项目开发遵循 SMART 软件工程思想，需求、任务和验收标准应尽量做到具体、可衡量、可达成、相关且有明确时间或阶段边界。
5. 每次完成一个较大的 change 后，必须完成实现、测试和验证，再使用中文 Git 提交信息提交，保持工作区干净。

## TDD 执行规范

1. 新增功能、修复缺陷或调整核心逻辑时，应优先使用 TDD 的红绿重构流程：先写失败测试，再写最小实现，最后在测试保护下重构。
2. 红灯阶段要让测试明确表达预期行为或缺陷复现点，避免只写无法约束实现的空测试。
3. 绿灯阶段只实现让测试通过所需的最小代码，不借机扩大功能范围或引入过度设计。
4. 重构阶段必须保持测试通过，重构目标应聚焦命名、结构、重复逻辑和可读性，不改变已验证行为。
5. 无法先写测试时，应在交付说明中解释原因，并补充可执行的验证方式、手工验证证据或后续测试补齐点。
6. 测试覆盖应优先保护核心业务规则、边界条件、回归缺陷和当前 change 的验收标准。

## Test-First PR 提交规范

1. 功能 PR 的重点不是提交代码量，而是先用测试定义需求、边界和验收标准；实现代码可以由 Agent 生成，但研发人员必须负责测试设计、结果验证和代码审查。
2. 功能分支必须按以下顺序组织提交：`test: add failing tests for xxx`、`impl: make xxx tests pass`、`refactor: clean up without behavior changes`、`chore: config / formatting / generated files`。
3. `test:` commit 只允许包含测试相关内容，例如 `Tests/`、`Fixtures/`、`Mocks/`、期望结果和测试辅助工具；测试应表达需求和验收标准，覆盖主要路径和关键边界，并且在没有实现 commit 时原则上应失败。
4. `test:` commit 不允许包含业务实现、生产代码改动或为通过测试而提前加入的功能逻辑。
5. `impl:` commit 只提交让测试通过的最小实现，不夹带无关功能、不做大范围重构、不实现未被测试覆盖的行为。
6. `refactor:` commit 只能在测试已通过后清理命名、结构、重复逻辑或可读性，不改变已验证行为。
7. `chore:` commit 只放配置、格式化、锁文件或生成文件等非业务变更；不得把功能实现或测试需求混入 `chore:`。
8. 不合格情况包括：测试和实现混在一个 commit、先写实现后补测试、实现超出测试覆盖范围、PR 夹带无关 UI、网络、缓存、埋点或过程产物。
9. 文档修改、纯格式化、CI 配置修复、依赖锁文件更新、删除无用代码和紧急线上修复可不强制 test-first，但必须在 PR 中说明原因；紧急修复后续必须补测试。
10. 没有清晰测试的功能 PR，不进入实现代码审查；Agent 只能协助生成实现，测试、边界和最终质量由提交人负责。

## SMART 执行规范

1. `Specific`：需求、任务和 change 必须描述清楚要解决的问题、目标用户、影响范围和不做事项，避免模糊表述。
2. `Measurable`：每个任务都应有可验证的验收标准，优先使用测试、lint、接口响应、页面状态、日志或文档检查作为衡量依据。
3. `Achievable`：方案应符合当前项目资源、技术栈和时间约束，优先选择 MVP 范围内可以落地的最小实现。
4. `Relevant`：实现内容必须服务于当前需求和 change，不引入与目标无关的重构、依赖、功能或文档扩展。
5. `Time-bound`：较大的任务应拆成有阶段边界的步骤，明确本次完成范围、后续延迟项和交付检查点。
6. 交付总结应回到 SMART 标准，说明目标是否完成、验收是否可衡量、范围是否受控，以及是否存在延期或后续事项。

## README 编写规范

1. README 必须按用户指定的目录层级编写；如果用户要求为多个子目录分别编写 README，不应改为只写根目录 README。
2. README 内容应基于真实文件结构、配置和已有规范，不凭空描述不存在的功能、命令或目录。
3. README 应优先包含目录定位、核心功能、文件结构、角色分工、多 Agent 协作约定、验收标准和维护原则。
4. 文件结构示例必须与当前目录实际结构保持一致；结构变更后应同步更新 README。
5. README 应保持 MVP 风格，说明必要信息即可，不写营销化、空泛化或与项目无关的内容。
6. README 的验收标准应可检查，至少能验证关键文件是否存在、目录位置是否正确、规范是否覆盖、单文件行数是否符合要求。

## docs 目录规范

1. 项目文档应按类型写入 `docs/` 下的对应子目录，避免把 PRD、计划、设计、验收和运维文档混放。
2. `docs/prd/` 存放产品需求、范围定义、用户故事和 MVP 边界。
3. `docs/plans/` 存放执行计划、阶段拆解、任务清单和排期安排。
4. `docs/design/` 存放技术方案、架构决策、接口设计和实现设计。
5. `docs/acceptance/` 存放验收标准、测试记录、验证报告和回归证据。
6. `docs/operations/` 存放发布流程、Git/PR 规范、部署说明和运行手册。
7. `docs/` 只存放会对项目产生长期真实影响的文档，例如需求边界、设计决策、验收标准、发布流程和运维规范。
8. 执行 todo、临时任务清单、过程性进展记录、一次性排查记录不应写入 `docs/`；这类内容应在任务清单、Workpad、issue 或 PR 中执行和收口。
9. 正式 docs 文档必须使用 YAML frontmatter 描述 `layer`、`doc_no`、`audience`、`purpose`、`owner`、`inputs`、`outputs`、`triggers` 和 `downstream` 等元信息。
10. `docs/TEMPLATE.md` 是正式文档模板，新增 PRD、计划、设计、验收或运维文档时应优先复用。
11. 每个 docs 子目录必须有 README，说明该目录放什么、不放什么，以及文档命名建议。

## Symphony-ready 编排原则

1. 复杂开发任务优先以 Linear ticket 为执行单位，而不是以一次聊天会话为执行单位。
2. 推荐落地顺序为 `Harness -> Orchestration -> Linear`：先补齐项目自启动、自验证和文档结构，再配置 `WORKFLOW.md`，最后接入 Linear 状态机。
3. 每个被调度的 ticket 应在隔离 workspace 中执行，Agent 只能操作当前 workspace 和本任务相关文件。
4. `CLAUDE.md` 记录长期稳定的 Claude 行为准则；项目级 `WORKFLOW.md` 记录 Linear project、workspace root、hooks、agent command、并发数等调度配置。
5. Agent 应先计划和设计验收方式，再实现；先复现或确认当前行为，再修改代码或文档。
6. Agent 必须自治执行到可审查结果，只有缺少必要权限、secret、外部服务或工具时才可以阻塞。

## Linear Ticket 状态机

推荐状态流为 `Backlog -> Todo -> In Progress -> Human Review -> Merging -> Done`，并保留 `Rework` 返工路径。

1. `Backlog`：不自动执行，等待人工明确移动到 `Todo`。
2. `Todo`：可被 Symphony 或兼容 runner 拾取；拾取后应立即移动到 `In Progress`。
3. `In Progress`：Agent 正在隔离 workspace 中执行计划、实现和验证。
4. `Human Review`：PR、验证证据和 Workpad 已准备好，等待人工审查。
5. `Merging`：人工批准后进入合并流程；合并前仍需检查 CI、冲突和目标分支状态。
6. `Done`：终态，runner 不再处理。
7. `Rework`：审查后需要返工，必须重新读取 ticket、评论、PR 反馈和当前代码状态，再重新计划。

## Workpad 单一事实源

1. 每个 Linear ticket 只维护一个持久评论作为进度事实源，Claude 使用标题 `## Claude Workpad`。
2. Workpad 应包含环境戳，格式为 `<hostname>:<abs-workdir>@<short-sha>`。
3. Workpad 必须维护 `Plan`、`Acceptance Criteria`、`Validation`、`Notes` 和必要时的 `Confusions`。
4. Ticket 描述、评论、change、PR 反馈中的验收要求必须同步到 Workpad 的验收和验证清单。
5. 计划、进度、验证、阻塞和交付说明都更新到同一个 Workpad，不额外散落多个总结评论。

## Harness 能力要求

1. 项目应提供一键启动入口，例如 `scripts/start-local.sh`、`make start` 或等价命令。
2. 项目应提供统一验证入口，例如 `npm test`、`scripts/verify.sh` 或等价命令。
3. 项目应说明 `.env.example`、secret 来源、本机与 CI 差异、日志位置和常见故障处理方式。
4. Agent 应优先使用可重复验证方式证明变更有效，包括测试输出、构建结果、接口响应、日志、截图、trace 或录屏。
5. 前端、网页和 UI 任务推荐使用 Playwright、截图、trace 或录屏作为验收证据；第一版不强制所有项目自动上传视频到 Linear。
6. 需要补齐本地启动和健康检查时，优先使用 `.claude/skills/harness-local-server/SKILL.md`。
7. UI 或前端任务需要端到端证据时，优先使用 `.claude/skills/harness-playwright-evidence/SKILL.md`。
8. 需要同步 Linear 状态、Workpad、PR 链接和证据时，优先使用 `.claude/skills/harness-linear-loop/SKILL.md`。

## Human Review 门禁

进入 `Human Review` 前必须满足：

1. Workpad 中的计划、验收标准和验证清单已更新，完成项已勾选。
2. Ticket 明确要求的 `Validation`、`Test Plan` 或 `Testing` 已执行。
3. 最新提交对应的测试、lint、构建或运行时验证通过。
4. PR 已创建或更新，并与 Linear ticket 关联。
5. PR 检查为绿色；如果项目没有配置检查，必须明确说明 `statusCheckRollup` 或等价检查为空。
6. PR feedback sweep 已完成，没有未处理的 actionable 评论。
7. UI 或前端任务已提供适当的截图、trace、录屏或可复现手工证据。

## Rework 与 Blocked 规则

1. `Rework` 是完整返工流程，不是在旧分支上随手补丁。
2. 进入 `Rework` 后必须重新读取 ticket、Workpad、PR 评论、人类反馈和最新 `origin/main`。
3. 如果旧 PR 已关闭、已合并或实现方向不可复用，应关闭旧 PR 或明确废弃旧状态，再从 `origin/main` 新建分支。
4. `Blocked` 只用于真实外部阻塞，例如缺少必要权限、secret、Linear/GitHub 工具、外部服务访问或不可替代的人工输入。
5. 阻塞时必须在 Workpad 写清楚缺什么、为什么阻塞、需要人做什么；不得把普通实现困难当作阻塞。

## 角色协作结构

当前项目支持 Codex、Claude 和 Cursor 三套多 Agent 入口并存；不得把一套入口替换为另一套入口。Claude 侧按 `CLAUDE.md + CLAUDE.local.md + .claude/agents/*.md` 的方式组织协作规则：

1. `CLAUDE.md` 记录 Claude 侧长期稳定的全局协作规则、验收要求和输出格式。
2. `CLAUDE.local.md` 记录放在具体项目中的局部规范性配置，用于和全局规则区分。
3. `.claude/agents/*.md` 记录 Claude 可识别的具体角色、职责边界、输入输出和执行约束。
4. `AGENTS.md + AGENTS.local.md + .codex/agents/*.toml` 记录 Codex 侧对应规范。
5. `CURSOR.md + CURSOR.local.md + .cursor/agents/*.md + .cursor/skills/* + .cursor/rules/*.mdc` 记录 Cursor 侧对应规范。
6. 三套入口应表达同一组项目约束，只按工具识别方式拆分，不互相替代。
7. 复杂任务优先使用多角色协作；简单任务可合并为 `PM -> Builder -> Tester` 三段式执行。
8. 角色越专一，协作越稳定；不要让单个角色同时承担需求拆解、实现、验证和总结的全部职责。

## 并行拆分与主代理清洁收口补充（新增）

1. 大任务必须先由 PM 或主代理产出任务拆分与并行执行计划。
2. 同一大任务可按子任务并行派发给专门角色，例如多个 `Explorer`、`Builder` 或 `Tester` 并行处理独立子任务。
3. 子角色交付必须是清洁结果：任务产出、证据路径、交付边界、风险项、验证结果。
4. 主代理只做收口：对齐边界、合并冲突、整理证据，不复述中间推演过程。
5. 出现交付冲突时，主代理只回访相关子角色补齐，不让未闭环信息进入最终交付。

## 标准角色与职责

1. `PM`：负责按 SMART 原则拆解需求、定义范围、制定验收标准、控制 MVP 边界。
2. `Explorer`：负责读取代码、查找文件、梳理依赖、提供事实依据。
3. `Builder`：负责制定最小实现方案，并在既有风格内完成代码或文档改动；涉及逻辑改动时应遵循 TDD 红绿重构流程。
4. `Tester`：负责测试、lint、回归检查和 TDD 红绿重构结果确认。
5. `Reporter`：负责汇总修改内容、验证证据、残余风险和交付说明。
6. 角色分类与定位：
   - PM：策略分解层。
   - Explorer：事实核验层。
   - Builder：实现执行层。
   - Tester：质量保障层。
   - Reporter：交付复盘层。

## 角色模型分配（仅使用以下模型）

1. `PM`：默认 `gpt-5.4`，复杂度高/边界冲突大时升级到 `gpt-5.5 medium`。
2. `Explorer`：默认 `gpt-5.4`，大规模检索或证据链复杂时切换到 `gpt-5.5 medium`。
3. `Builder`：默认 `gpt-5.3-codex-spark`，复杂场景不足时可回退到 `gpt-5.4`，关键任务仍可直接升用 `gpt-5.5 medium`。
4. `Tester`：默认 `gpt-5.4`，复杂验证链路可升到 `gpt-5.5 medium`。
5. `Reporter`：默认 `gpt-5.4`，多方证据汇总时可升到 `gpt-5.5 medium`。

## 标准执行流程

复杂任务按以下顺序执行：

`Explorer -> PM -> Builder -> Tester -> Reporter`

1. `Explorer` 先收集上下文，避免在不了解现有结构时直接设计。
2. `PM` 根据上下文拆分任务，明确范围、验收标准和不做事项。
3. `Builder` 只实现验收所需的最小变更。
4. `Tester` 使用红绿测试、lint 或回归检查验证结果。
5. `Reporter` 输出改了什么、如何验证、还有哪些风险。

## 较大 change 收口规范

1. 较大 change 必须完成实现、测试、验证和交付说明后再收口。
2. change 未完成测试或验收前，不得进行最终 Git 提交。
3. Git 提交前应检查工作区，只提交本次已完成 change 的相关文件，保持任务完成后的工作区干净。
4. 如果 change 暂时不能收口，应在交付说明中明确阻塞原因、剩余事项、当前验证状态和工作区状态。

## Git 提交规范

1. 每次完成较大的 change 后，应先完成测试和验证，再使用中文 Git 提交信息提交本次改动。
2. 提交前必须检查工作区范围，确认只包含本次 change 相关文件；无关修改不得混入提交。
3. 功能 PR 必须优先使用 `test:`、`impl:`、`refactor:`、`chore:` 的提交顺序；单个提交应保持职责单一，不能混合测试、实现、重构和配置变更。
4. 非功能类提交信息应简洁说明核心结果，优先使用 `fix:`、`docs:`、`ci:`、`chore:` 等类型前缀。
5. 中间产物、临时文件、一次性报告、本地缓存、测试输出目录和调试日志不需要提交到 GitHub；如果必须保留长期证据，应沉淀为正式 docs 文档或验收记录。
6. 提交后应再次检查工作区状态，确认没有遗漏文件、未暂存文件或意外生成物。
7. 如果用户明确要求暂不提交，应在交付说明中记录原因、当前工作区状态和后续提交建议。

## PR 提交与合并规范

1. 创建或更新 PR 前，应先确认分支、提交范围、验证结果和是否存在可复用的已有 PR。
2. PR 标题和描述应使用中文，说明修改内容、验证方式、影响范围、风险和 change 状态。
3. 同一任务已有 PR 时，应优先更新现有 PR，不要无意义创建重复 PR。
4. PR 合并前必须检查状态、CI、冲突和目标分支最新状态；不能只因为代码已完成就直接合并。
5. 每次 PR 合并前必须先给当前目标分支状态打 tag，作为合并前回滚点；tag 名称应能体现合并对象和日期，例如 `pre-merge-pr12-20260508`。
6. 多个 PR 需要合并时，应按用户指定顺序逐个合并；每合并一个 PR 后都要重新检查后续 PR 的冲突、CI 和合并状态。
7. PR 合并后应同步本地分支状态，并执行必要的仓库健康检查，确认没有合并后遗留的工作区污染或格式问题。
8. 功能 PR 描述必须包含 Test-first Evidence、Tests added、Commands run、Result、Agent Usage 和 Reviewer Checklist；Reviewer 应先审 `test:` commit，再审 `impl:` commit。
9. CI 必须包含完整测试入口，至少运行仓库结构检查、Markdown 空白检查和 `npm test`；项目增加真实单元、集成、UI、快照或性能测试后，应把对应命令接入 `npm test` 或 CI 明确步骤。

## PR 模板要求

功能 PR 描述必须覆盖以下内容：

````markdown
# PR Summary

## Test-first Evidence

- Failing test commit:
- Test fails before implementation:
  - [ ] Yes
  - [ ] No
  - [ ] Not applicable

## Tests added

- [ ] Unit
- [ ] Integration
- [ ] UI
- [ ] Snapshot
- [ ] Performance

## Commands run

```bash
# test command
```

## Result

- Failed before implementation
- Passed after implementation

## Agent Usage

Human-authored:
- Acceptance criteria:
- Test cases:
- Edge cases:

Agent-generated:
- Implementation:
- Refactor:
- Boilerplate:

## Reviewer Checklist

- [ ] Test commit reviewed first
- [ ] Tests express requirement
- [ ] Edge cases covered
- [ ] Implementation is minimal
- [ ] No unrelated changes
- [ ] Agent code reviewed
- [ ] CI passed
````

## 交付输出要求

每次任务完成时，输出至少包含：

1. 修改了什么。
2. 如何验证。
3. 是否存在未验证内容或残余风险。
4. 涉及的关键文件。
5. Git 提交状态：是否已中文提交、提交信息是什么、工作区是否干净。
6. PR 状态：是否已创建或更新 PR、是否需要合并、合并前 tag 是否已创建。
