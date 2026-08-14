---
name: director-breakdown
description: 按真实 Cut 拆解镜头语言、叙事作用、高光价值与制作建议。用于完整视频的导演拉片分析。
license: MIT
metadata:
  video-server-display-name: 导演拉片
  video-server-default-prompt: 逐镜头分析画面、景别、运镜、叙事作用和高光价值，并给出可执行的 AI 漫剧制作建议。
  video-server-order: "10"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
---
# 导演逐镜头拉片

逐个观察视频中的真实 Cut，不得把固定时长切片冒充镜头。每个镜头必须记录起止时间、代表帧、画面内容、转场、景别、摄影机运动、叙事作用、高光等级、视觉标签和可复用资产。

## 分析要求

1. 镜头边界以剪辑点、场景变化或连续动作语义变化为依据。
2. 画面描述只写可见事实；不确定的身份、地点和因果不得臆测。
3. 叙事作用需说明该镜头在信息交代、情绪推进、人物塑造、冲突或节奏上的功能。
4. 高光等级使用 1 至 5 分；4 至 5 分镜头应在 highlights 中说明原因。
5. 资产目录需覆盖重要角色、场景、道具、界面、文字或图形元素，并绑定证据镜头。
6. production_advice 必须总结复刻策略、优先镜头和可延展方向，建议应可直接用于 AI 漫剧制作。

输出内容必须完整支撑“基础信息与逐镜头表格、高光镜头分析、AI 漫剧制作建议”三部分报告。
