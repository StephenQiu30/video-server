---
name: highlights
description: 用统一量表筛选视觉冲击、信息转折、情绪变化和可剪辑性兼具的片段。用于高光、预告和传播素材候选提炼。
license: MIT
metadata:
  video-server-display-name: 高光提炼
  video-server-default-prompt: 完整观察后按视觉显著性、信息或情绪转折、上下文独立性、可剪辑性和连续性风险筛选高光，并解释取舍。
  video-server-order: "40"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/highlight-rubric.md
---
# 高光提炼

先保证全片镜头结构正确，再筛选少量、互有差异且可复核的高光候选。高光可以是单镜，也可以是完成同一节拍的连续镜头组合；不能把全部镜头打高分，也不能只凭标题、台词或主观“好看”判断。

## 选择原则

1. 对所有候选使用同一量表，优先保留在视觉显著性、信息/情绪转折、上下文独立性或可剪辑性上有明确优势的片段。
2. 高光范围应包含完整的可见动作或转折，避免从动作中间开始、在结果出现前结束。
3. 同质候选只保留证据最完整、构图最清晰或转折最充分的一项，并在理由中说明其差异。
4. `evidence_shot_ids` 必须位于候选范围内；`score` 是本次视频内的相对评分，不代表播放量、转化或受众偏好。
5. `production_advice` 可提出预告/复刻/封面候选的下一步验证，但不得声称已经发布或选定。

所有高光结果都是待比较候选，不是用户已经确认的主选或平台效果结论。

量表、去重规则和完整性检查见 `references/highlight-rubric.md`。最终只返回 `video-visual-analysis` Schema。
