# 012 剧本分析 Skill 选型与接入记录

- 复核日期：2026-09-24
- 范围：已上传的规范化剧本文本；综合、短剧、人物、场景、对白、结构和连续性审阅；严格 `screenplay-analysis` JSON 契约

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

两个上游仓库的选定原始 Markdown 文件及 MIT 许可证现已直接纳入 `backend/app/services/analysis/skills/modules/`，保持原文不改。`modules.py` 固定每个文件的 SHA-256 和运行时加载的标题章节。Skill 使用 `video-server-modules` 声明依赖；加载器把上游原文中的指定章节编译进不可变任务指令快照，而不是仅依据来源重写。本次综合审稿编译 7 个模块，约 43,000 字符；专项 Skill 只加载相关模块。完整原始文件保留用于复核，未选中的写作练习、固定页码、文件交付、其他媒体工作流不进入模型上下文，也没有安装脚本、代理流程或运行时网络能力。

## 已接入的规则

- `screenplay-analysis` 同时加载两库共 7 个审稿模块，先形成优先修改决策，再综合结构、人物、场景和对白。
- 新增 `screenplay-drama-review`、`screenplay-character-review`、`screenplay-scene-review`、`screenplay-dialogue-review` 四个可直接选择的专项 Skill；原有 `screenplay-structure-review` 和 `screenplay-continuity-review` 也加载相应上游模块。
- 项目适配层保留已上传剧本、源场景覆盖和 JSON 输出契约。上游内容是可按文本条件使用的诊断工具，不把固定幕数、页码、人物成长或类型口味作为一律阻断的规则。
- 结构化输出仍由服务端严格 Schema、覆盖校验和报告渲染控制。上游 Skill 的文件写入、工具调用及创作流程不执行。

Context7 对 [Pydantic JSON Schema](https://github.com/pydantic/pydantic/blob/main/docs/concepts/json_schema.md) 的资料确认数组 `min_length` 对应 `minItems`。本项目 AI 输出 Schema 为受限手写契约；场景覆盖与幕结构由服务端验证。`strengths` 和 `priority_revisions` 允许空数组：审稿没有充分依据时应明确留空，不能为了通过校验制造赞扬或批评。

## 接入边界

上游 Star 和写作方法不能替代对具体剧本的事实核查。`source_scene_id` 只校验 1:1 覆盖与顺序，不是截图或原文引用。旧 Skill 快照不自动改写，版本变化时旧任务重试返回 `analysis_skill_outdated`，由用户使用当前 Skill 新建任务。
