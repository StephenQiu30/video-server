# 012 剧本分析 Skill 选型与接入记录

- 复核日期：2026-09-24
- 范围：已上传的规范化剧本文本；现有 `screenplay-analysis`、`screenplay-structure-review`、`screenplay-continuity-review`；严格 `screenplay-analysis` JSON 契约

## 来源与判断

使用 Firecrawl 搜索编剧 Agent Skill，用 GitHub 仓库资料核对 Star、许可证与维护状态，并用 Context7 核对 Pydantic 的数组长度和 JSON Schema 行为。Star 只是社区采用程度的参考，不能证明分析准确性、提示词安全或与本项目契约兼容。

| 候选来源 | GitHub Star（复核时） | 许可证 | 结论 |
| --- | ---: | --- | --- |
| [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) | 2,229 | MIT | `short-drama-review` 提供问题、文本表现、影响和修改目标的审稿方法；接入其适用的判断顺序与去重原则。 |
| [jtydhr88/screenwriting-skills](https://github.com/jtydhr88/screenwriting-skills) | 1,375 | MIT | `sw-scene-craft`、`sw-character-conflict`、`sw-dialogue`、`sw-story-structure` 提供场景、人物、对白与结构维度；选取适用规则。 |
| [jwynia/agent-skills](https://github.com/jwynia/agent-skills) | 160 | 各 Skill 声明 MIT；仓库无统一许可证 | 概念与现有规则重叠；不引入运行时内容。 |
| [rouql/AI-Drama-Skill](https://github.com/rouql/AI-Drama-Skill) | 1 | MIT | 偏多 Agent 短剧创作和市场分析，与当前受限文本审阅边界不符；不接入。 |
| [ur-grue/autopunk-media-skills](https://github.com/ur-grue/autopunk-media-skills) | 33 | MIT | 以媒体制作通用任务为主，当前剧本解析没有缺失对应工具能力；不接入。 |

`drama-skills` 固定参考 [`b71cb3ca9343eaf6c0375725ccc9261a4e79021e`](https://github.com/zenstory-ai/drama-skills/tree/b71cb3ca9343eaf6c0375725ccc9261a4e79021e) 的 `short-drama-review` 及其 `review-method`、`rubric-story-script`、`anti-template-repair`；`screenwriting-skills` 固定参考 [`357d1348ccaa1ab75f2f51ef7c90a7f00a686c76`](https://github.com/jtydhr88/screenwriting-skills/tree/357d1348ccaa1ab75f2f51ef7c90a7f00a686c76)，其 `LICENSE` 标明 Copyright (c) 2026 Terry Jia，MIT。Star 是 2026-09-24 查询时的快照。

这些上游 Skill 的完整文件面向可写文件、调用工具或多步骤创作的 Agent。本项目的 Analysis 执行器仅加载 `SKILL.md` 和一层 `references/*.md`，输入限定为已上传剧本，输出限定为严格 JSON。直接复制完整上游文件会引入不适用的文件交付和工具指令，因此把经过审查的审稿方法写入当前内置 Skill；没有安装脚本、代理流程或运行时网络能力。这里的“接入”是运行时实际加载的规则内容，而不只是来源清单。

## 已接入的规则

- `screenplay-analysis` 改为故事审稿，先识别最重要的修改决策，再审结构、人物、场景和对白；内置 `review-method.md` 明确“文本表现 → 影响 → 修改目标”、问题优先级和跨场去重。
- 专项规则增加人物自述与压力下选择的区分、场景前后状态比较、对白意图与回应的核查。每条结论须以本次文本可见内容为范围；无法确认时写出限制。
- `screenplay-structure-review` 增加动作与反应的顺序、重复策略是否升级压力的检查。
- 现有连续性审阅继续区分明确矛盾、过渡缺口与有意留白，避免把省略自动判为错误。
- 结构化输出仍由服务端严格 Schema、覆盖校验和报告渲染控制。上游 Skill 的自由文本输出、创作流程、工具调用和固定页码模板均未引入。

Context7 对 [Pydantic JSON Schema](https://github.com/pydantic/pydantic/blob/main/docs/concepts/json_schema.md) 的资料确认数组 `min_length` 对应 `minItems`。本项目 AI 输出 Schema 为受限手写契约；场景覆盖与幕结构由服务端验证。`strengths` 和 `priority_revisions` 允许空数组：审稿没有充分依据时应明确留空，不能为了通过校验制造赞扬或批评。

## 接入边界

上游 Star 和写作方法不能替代对具体剧本的事实核查。此次变更移除了会被误读为截图或原文引用的模型生成场景证据字段；`source_scene_id` 只校验 1:1 覆盖与顺序。旧 Skill 快照不自动改写，版本变化时旧任务重试返回 `analysis_skill_outdated`，由用户使用当前 Skill 新建任务。
