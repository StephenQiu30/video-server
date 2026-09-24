# 012 剧本分析 Skill 选型与接入记录

- 复核日期：2026-09-24
- 范围：已上传的规范化剧本文本；现有 `screenplay-analysis`、`screenplay-structure-review`、`screenplay-continuity-review`；严格 `screenplay-analysis` JSON 契约

## 来源与判断

使用 Firecrawl 搜索编剧 Agent Skill，用 GitHub 仓库资料核对 Star、许可证与维护状态，并用 Context7 核对 Pydantic 的数组长度和 JSON Schema 行为。Star 只是社区采用程度的参考，不能证明分析准确性、提示词安全或与本项目契约兼容。

| 候选来源 | GitHub Star（复核时） | 许可证 | 结论 |
| --- | ---: | --- | --- |
| [jtydhr88/screenwriting-skills](https://github.com/jtydhr88/screenwriting-skills) | 1,373 | MIT | 有较完整的场景、结构、人物与对白审阅体系；选取适用的判断维度，重写进现有内置 Skill。 |
| [rouql/AI-Drama-Skill](https://github.com/rouql/AI-Drama-Skill) | 1 | MIT | 偏多 Agent 短剧创作和市场分析，与当前受限文本审阅边界不符；不接入。 |
| [ur-grue/autopunk-media-skills](https://github.com/ur-grue/autopunk-media-skills) | 33 | MIT | 以媒体制作通用任务为主，当前剧本解析没有缺失对应工具能力；不接入。 |

选用来源固定为 [`357d1348ccaa1ab75f2f51ef7c90a7f00a686c76`](https://github.com/jtydhr88/screenwriting-skills/tree/357d1348ccaa1ab75f2f51ef7c90a7f00a686c76)，仓库 `LICENSE` 标明 Copyright (c) 2026 Terry Jia，MIT。参考了其中 `sw-scene-craft`、`sw-character-conflict`、`sw-dialogue`、`sw-story-structure` 的审阅维度，没有复制原 Skill 文件、示例或外部脚本。

## 已接入的规则

- `screenplay-analysis` 的文本规则增加人物自述与压力下选择的区分、场景前后状态比较、对白意图与回应的核查。每条结论须以本次文本可见内容为范围；无法确认时写出限制。
- `screenplay-structure-review` 增加动作与反应的顺序、重复策略是否升级压力的检查。
- 现有连续性审阅继续区分明确矛盾、过渡缺口与有意留白，避免把省略自动判为错误。
- 结构化输出仍由服务端严格 Schema、覆盖校验和报告渲染控制。上游 Skill 的自由文本输出、创作流程、工具调用和固定页码模板均未引入。

Context7 对 [Pydantic JSON Schema](https://github.com/pydantic/pydantic/blob/main/docs/concepts/json_schema.md) 的资料确认数组 `min_length` 对应 `minItems`。本项目 AI 输出 Schema 为受限手写契约；至少一个幕、优势和优先修改项由服务端结果校验明确执行，不能只靠提示词或忽略的 Schema 参数。

## 接入边界

上游 Star 和写作方法不能替代对具体剧本的事实核查。此次变更移除了会被误读为截图或原文引用的模型生成场景证据字段；`source_scene_id` 只校验 1:1 覆盖与顺序。旧 Skill 快照不自动改写，版本变化时旧任务重试返回 `analysis_skill_outdated`，由用户使用当前 Skill 新建任务。
