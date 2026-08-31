---
name: editing-rhythm-review
description: 审阅成片的视觉剪辑节奏、镜头停留、信息密度、切点动机和动作衔接。用于发现拖沓、无目的快切、信息过载与节奏断裂。
license: MIT
metadata:
  video-server-display-name: 剪辑节奏审阅
  video-server-default-prompt: 完整观察时间线，审阅镜头停留、视觉信息密度、切点动机、动作与构图衔接、段落内节奏变化，区分必要停留、拖沓、无目的快切和信息过载。
  video-server-order: "42"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/editing-rhythm-rubric.md
---
# 剪辑节奏审阅

目标不是追求更多 Cut 或统一镜头时长，而是判断每次停留和切换是否给观看者足够时间读懂画面，并让动作、信息和段落目标持续推进。

## 工作方法

1. 完整覆盖真实 Cut 级时间线，比较每镜的视觉信息量、主体动作、构图变化与停留时长。
2. 判断切点是否由动作完成、视线/主体变化、信息揭示、空间转换或段落转折支持。
3. 区分有目的停留、无变化拖延、重复信息、无目的快切和同一时刻的信息过载；镜头长短本身不直接代表好坏。
4. 纵向检查段落节奏是否形成可辨认的建立、加速、释放或收束，而不是只统计平均镜头时长。
5. 把修订建议落实到真实分镜与可验证结果，例如缩短重复停留、延长关键信息阅读、调整切点或减少同时竞争的视觉元素。

## 输出边界

- `summary` 概括全片节奏形态、最清晰的有效段落与首要节奏风险。
- 分镜 `narrative_function` 说明停留或切换的用途；`visual_tags` 使用参考量表中的节奏与切点前缀。
- `production_advice` 必须给出分镜证据和期望结果，不给出脱离素材的固定秒数公式。
- 当前没有可靠音频证据时，不评价音乐卡点、语速、停顿、音效或声音桥。

具体量表、标签和特殊情况见 `references/editing-rhythm-rubric.md`。最终只返回 `video-visual-analysis` Schema。
