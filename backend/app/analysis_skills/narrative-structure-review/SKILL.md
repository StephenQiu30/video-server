---
name: narrative-structure-review
description: 审阅成片的可见叙事结构、段落推进、转折、兑现与因果可读性。用于故事短片、产品演示、解说和需要判断“是否讲清楚”的视频。
license: MIT
metadata:
  video-server-display-name: 成片叙事结构审阅
  video-server-default-prompt: 完整覆盖成片并区分真实编辑边界与连续视觉节拍，按可见证据审阅建立、推进、转折与兑现，找出重复、跳步和承诺未兑现的段落。
  video-server-order: "37"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/narrative-rubric.md
---
# 成片叙事结构审阅

目标是回答成片如何建立问题或承诺、怎样推进、在哪里改变方向、最终兑现了什么。只使用画面、可辨认文字和真实时间线，不把想象中的脚本、对白或创作者意图当作事实。

## 工作方法

1. 先建立完整 `shots` 与连续 `scenes`，再从相邻段落归纳结构；`shots` 同时覆盖物理编辑和连续长镜头内的任务阶段，不得因没有 Cut 就把多次可见推进压成一项，也不得先套三幕模板。
2. 区分建立、推进、升级、转折、兑现和收束，并检查相邻段落是否具有可见的状态变化或信息承接。
3. 标出重复但没有新增信息的段落、缺少视觉前提的跳步、建立后未兑现的承诺，以及兑现出现但准备不足的位置。
4. 建议以“观察 → 理解影响 → 期望修订结果”表达，并引用真实 `shot.id`；可建议前移、后置、合并、缩短或补充人工核对，不自动改片。

## 输出边界

- `summary` 写全片结构主线、最强转折或兑现，以及优先结构风险。
- `narrative_function` 写本镜头或场景在可见推进中的具体作用；`continuity_risks` 可记录因果或信息承接风险。
- `highlights` 只收录真正承担结构转折或兑现的候选；`production_advice` 按叙事影响排序。
- 没有可靠音频证据时，不评价台词逻辑、旁白信息、音乐结构或声音桥；不预测留存、完播或转化。
- 连续阶段边界使用 `transition_in=continuous`，边界成立但类型不明时使用 `unknown`；不得用固定秒数制造虚假推进。

具体结构标签、判断规则和字段映射见 `references/narrative-rubric.md`。最终只返回 `video-visual-analysis` Schema。
