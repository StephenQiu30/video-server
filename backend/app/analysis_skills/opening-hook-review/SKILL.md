---
name: opening-hook-review
description: 审查视频开场前 3、5 和 15 秒的可见注意力锚点、内容承诺、画面文字、视觉进展与正文衔接。用于短视频、口播和产品片的开场优化。
license: MIT
metadata:
  video-server-display-name: 开场钩子审查
  video-server-default-prompt: 完整观察全片，重点审查开场前 3、5 和 15 秒的主体锚点、内容承诺、文字可读性、有意义的画面变化和进入正文的衔接，并给出引用真实分镜的优先修订建议。
  video-server-order: "45"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/opening-hook-rubric.md
---
# 开场钩子审查

目标是用可复核的画面证据回答：观众最先看到什么、开场承诺了什么、画面如何持续推进，以及这个承诺是否在后续画面中兑现。它不预测平台留存率，也不用主观的“吸引人”代替具体观察。

## 执行流程

1. 先覆盖完整时间轴并建立真实 Cut 级 `shots` 和连续 `scenes`；不得因聚焦开场而省略后续内容。
2. 分别审查 0–3 秒的注意力锚点、0–5 秒的可见内容承诺和 0–15 秒的视觉进展；视频更短时截断到权威时长。
3. 检查主体、动作、构图、画面文字、状态变化、镜头变化和进入正文的衔接。区分有目的进展、无变化停滞、无意义快切与信息过载。
4. 用后续分镜检查开场的视觉承诺是否兑现；不把想象中的台词、音效或发布表现当作证据。
5. 把结论写成“可见观察 → 对理解或节奏的影响 → 必须达到的修订结果”，并引用真实 `shot.id`。

## 输出纪律

- `summary` 概括开场最强证据、最大风险和后续兑现情况，不编造总分或平台指标。
- 开场分镜的 `visual_tags` 使用量表中的受控前缀；`description` 和 `narrative_function` 仍保留可见事实、起止状态与镜头任务。
- `highlights` 只保留少量真正支持开场判断的候选；没有成立候选时返回空数组，不为满足数量而虚构优势。
- `production_advice` 按影响和可执行性排序，明确哪些分镜应保留、前移、简化、放大、重组或进一步人工复核。
- 高光分数只用于本结果内候选的相对比较，不表示停留、完播、点击、转化或审美概率。

## 边界

当前运行时没有可靠音频证据时，不评价开场台词、语速、音乐卡点、音效、口型或情绪语气。画面不足以支持判断时保留不确定性；审查结果是创作建议，不是自动剪辑、发布或市场效果承诺。

评估维度、标签、特殊情况和交付自检见 `references/opening-hook-rubric.md`。最终只返回 `video-visual-analysis` Schema。
