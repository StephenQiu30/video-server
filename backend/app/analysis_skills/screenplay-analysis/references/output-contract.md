# screenplay-analysis 输出契约

## 顶层结构

完整场景调用必须返回以下字段，字段名不能翻译、增加或删除：

```json
{
  "language": "zh-CN 或 en-US",
  "title": "...",
  "logline": "...",
  "synopsis": "...",
  "structure": {
    "acts": [],
    "turning_points": [],
    "pacing_summary": "..."
  },
  "characters": [],
  "scenes": [],
  "dialogue_findings": [],
  "strengths": [],
  "priority_revisions": []
}
```

汇总调用使用同一份全局结构，但不返回 `scenes`；执行器会把已经校验的分块场景结果合并回最终结果。

## ID 和证据

- 所有 `id` 都是不含空白的稳定字符串。推荐使用 `act-01`、`turn-01`、`character-01`、`scene-analysis-0001`、`finding-01` 等可读 ID；同一数组内不得重复。
- `source_scene_id` 必须逐字复制请求提供的 ID，只能来自权威列表。不得创建 `scene-1`、`场景一` 或其他替代名称。
- `evidence_scene_ids` 必须是非空数组，且每个值都来自权威列表；不能引用不存在的场景、字符偏移、块序号或模型推测。
- `scenes` 中每项只对应一个源场景，并且按输入列表原顺序出现：

```json
{
  "id": "scene-analysis-0001",
  "source_scene_id": "scene-0001-abc123",
  "purpose": "本场在故事中的功能",
  "conflict": "本场的目标与阻力",
  "turn": "本场结束时发生的可验证变化；没有变化就明确说明",
  "pacing": "节奏判断及其依据",
  "findings": ["具体、短而可执行的发现"]
}
```

## 证据条目

`acts`、`turning_points`、`dialogue_findings`、`strengths` 和 `priority_revisions` 使用相同形状：

```json
{
  "id": "finding-01",
  "title": "短标题",
  "description": "事实或诊断，以及为什么成立；不要泛泛评价",
  "evidence_scene_ids": ["scene-0001-abc123"]
}
```

`acts`、`strengths` 和 `priority_revisions` 至少返回一项；`turning_points` 和 `dialogue_findings` 在没有充分证据时可以为空数组。不要为了填充数组而生成重复或无证据的内容。

## 人物条目

```json
{
  "id": "character-01",
  "name": "原文中的人物名",
  "goal": "外部目标或稳定欲望",
  "conflict": "阻力、矛盾或关系压力",
  "arc": "选择、结果和变化；静态人物说明其稳定立场如何影响故事",
  "evidence_scene_ids": ["scene-0001-abc123"]
}
```

只列出对故事有独立作用的主要人物；临时群众、背景人物和只出现一次且没有叙事作用的名字不必单列。

## 与服务端报告的关系

这些 JSON 字段会由服务端渲染为固定章节：阅读摘要、故事概览、结构与节奏、人物分析、逐场景分析、对白与写作、文本优势、优先修改建议和证据说明。不要在字段内容中嵌套 Markdown 标题、表格、代码围栏、HTML、链接或整段原文。
