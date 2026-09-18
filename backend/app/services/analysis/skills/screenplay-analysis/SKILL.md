---
name: screenplay-analysis
description: 分析完整剧本的结构、人物、场景、节奏、对白与可执行修改建议。用于中文或英文剧本的证据优先综合审阅。
license: MIT
metadata:
  video-server-display-name: 剧本综合分析
  video-server-default-prompt: 按当前项目的 screenplay-analysis 结构化契约，分析故事结构、人物弧光、场景功能、节奏与对白，并按优先级给出有场景证据的修改建议。
  video-server-order: "60"
  video-server-input-kinds: screenplay
  video-server-output-contract: screenplay-analysis
  video-server-references: references/evidence-rules.md, references/output-contract.md
---

# 剧本综合分析

你正在为 Video Server 生成 `screenplay-analysis` 结构化结果。该 Skill 产出的是 editorial coverage（故事审阅），不是预算、排期或拍摄用的 production breakdown。服务端会把结果渲染为中文/英文 Markdown 报告，因此你只返回契约要求的 JSON，不返回 Markdown 报告。

## 执行目标

1. 先读取规范化剧本的全局因果，再按源场景完成场景、人物和证据分析。
2. 只使用请求中给出的 `source_scene_id`；它们是服务端生成的唯一证据坐标，不是可由模型改写的标签。
3. 事实、诊断和未知信息分开：正文没有证据时写出范围限制，不补写情节、结局、作者背景或制作条件。
4. 把长篇细节放在逐场景 `findings` 和有证据的条目中；全局 `logline`、`synopsis` 和 `pacing_summary` 只做可读的压缩总结，不复制原文。
5. 不生成正文没有证据的评分、市场表现、预算、排期、演员、道具、服化道、音效或视效信息。
6. `source_scene_id` 是剧本文本场景，不是剪辑镜头或固定时长分段；不得从页数、段落数或场景长度推断未来镜头数量。需要讨论可视化时只指出待覆盖事实和可拍动作。

## 结果质量

- `logline` 必须包含可验证的主角、目标、主要阻力和利害关系，控制在一到两句话。
- `synopsis` 覆盖开端、升级、关键选择/转折和结局；如果当前是分块调用，只总结当前块能证明的内容，不假装知道全剧结局。
- `acts` 按实际叙事组织，不强行套三幕；`turning_points` 只记录真正改变目标、信息、压力或选择的转折。
- 人物弧光使用“目标/欲望 → 阻力 → 选择 → 结果/变化”的证据链；不要把性格形容词当成弧光。
- 每场说明功能、冲突压力、场景转变和节奏；地点切换本身不是 `turn`。没有推进时要明确指出。
- `dialogue_findings` 关注角色声音、潜台词、关系变化、信息倾倒和对白的多重功能。
- `strengths` 说明具体有效机制；`priority_revisions` 按叙事影响和可执行性排序，指出问题与受影响场景，不代写未经请求的新剧情。

## 长剧本与分块调用

执行器可能先按完整场景分块，再用已校验的分块结果做汇总。分块不是新的剧本，也不是新的场景身份：

- 场景调用：`scenes` 必须逐一覆盖本次请求给出的场景 ID，保持输入顺序、不可遗漏、重复或重排；只对本块文本下结论。
- 汇总调用：只生成 `title`、`logline`、`synopsis`、`structure`、`characters`、`dialogue_findings`、`strengths` 和 `priority_revisions`，不要生成 `scenes`；只能综合分块结果中已有的证据。
- 不把分块边界当成幕边界，不因为场景在不同块中就制造重复人物、重复转折或互相矛盾的全局结论。
- 通过 `source_scene_id` 引用证据，不引用字符位置、模型自造场景号或“上一块/下一块”等不可验证坐标。
- 汇总前检查每个分块场景是否完整覆盖动作、对白归属和转折事实；不能用全局概括掩盖某一源场景的缺失或重复。

## 输出纪律

严格生成 `screenplay-analysis` 结果契约要求的 JSON，字段、数组对象和证据规则见 [output-contract](references/output-contract.md)。输出语言服从任务参数。最终只返回 JSON 对象，不附加 Markdown、代码围栏、解释或工具调用。
