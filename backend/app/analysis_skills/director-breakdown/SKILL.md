---
name: director-breakdown
description: 按真实 Cut 复盘调度、构图、镜头动机、剪辑关系、叙事节拍和复刻策略。用于完整视频的专业导演拉片。
license: MIT
metadata:
  video-server-display-name: 导演拉片
  video-server-default-prompt: 以导演工作台方式逐 Cut 拉片：复盘画面调度、镜头动机、剪辑关系、叙事节拍、连续性和可执行复刻策略。
  video-server-order: "10"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/director-method.md
---
# 导演拉片

目标不是罗列景别，而是解释每个 Cut 为什么存在、画面如何组织注意力、相邻镜头如何共同完成一个叙事节拍，以及这些观察如何转成可执行的复刻方案。

## 执行顺序

1. 先全片覆盖，再复核疑似边界；低对比转场、遮挡转场和同镜头内显著画面演化不能只靠固定阈值判断。
2. 对每镜分别记录可见事实、主体调度、构图/光色、摄影机行为、剪辑关系和叙事功能，禁止用风格形容词替代观察。
3. 纵向检查镜头序列：空间建立、视线/运动方向、动作衔接、景别变化、节奏转折和视觉母题。
4. 最后才评高光、资产和复刻优先级；建议必须能回指真实 `shot.id`。

## 输出纪律

- `description` 按“主体与动作；空间与构图；光线与色彩；镜头起止状态”写可见事实。无法从画面确认焦段、机位尺寸或创作者意图时不要猜。
- `narrative_function` 写“本镜头完成的节拍 + 与前后镜头的关系 + 判断依据”，不要只写“推进剧情”“营造氛围”。
- `visual_tags` 使用参考文档中的受控前缀，保留角度、构图、光色、连续性和节奏线索。
- 高光分数只是本次分析中的相对排序；资产只是身份候选；`production_advice` 只是制作建议，均不代表主选、审核或项目写入结果。
- 没有可靠音频证据时，不得把字幕、口型或画面文字推断成对白、音乐、音效或作者观点。

详细判读步骤、字段映射和交付自检见 `references/director-method.md`。最终只返回 `video-visual-analysis` Schema 所需字段。
