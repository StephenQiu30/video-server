---
name: comprehensive
description: 以证据链方式整合镜头结构、内容段落、节奏、高光、资产与制作策略。用于需要完整决策概览的视频分析。
license: MIT
metadata:
  video-server-display-name: 综合分析
  video-server-default-prompt: 完整覆盖视频并建立“镜头事实—段落结构—高光与资产—制作策略”证据链，指出关键转折、连续性风险和优先行动。
  video-server-order: "20"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/evidence-synthesis.md
---
# 综合视频分析

综合分析不是把其他模式各写一小段，而是把镜头事实组织成一条可复核的证据链：先回答画面发生了什么，再回答结构如何变化，最后给出候选价值和下一步制作策略。

## 执行流程

1. 连续覆盖全片并确认真实镜头边界。
2. 按视觉目标、空间、主体和节奏变化识别内容段落，并将其写入 `scenes`；每个场景连续覆盖相邻镜头且共同完成一个主要任务。
3. 从具体镜头归纳摘要、转折和视觉模式；所有归纳都引用真实 `shot.id`。
4. 分别建立高光候选与资产候选，再检查它们是否覆盖核心段落，而不是简单按数量平均分配。
5. 制作建议按影响、可执行性和连续性风险排序，明确优先镜头和验收条件。

## 工作边界

- 区分观察、解释、建议三种陈述；解释不得冒充事实，建议不得冒充已经执行的决策。
- 同一视觉身份跨镜头合并，状态变化要有画面证据；高光不是最终主选，资产不是已入库版本。
- 摘要应覆盖全片结构，不得只复述最醒目的开头或结尾。
- 无法由画面确认的对白、人物身份、因果、外部背景和传播结果不得补齐。

证据层级、段落归纳、冲突消解和交付检查见 `references/evidence-synthesis.md`。最终只返回 `video-visual-analysis` Schema。
