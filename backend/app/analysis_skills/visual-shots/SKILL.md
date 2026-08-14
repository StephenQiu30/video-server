---
name: visual-shots
description: 重点拆解构图、景别、运镜、转场、色彩与画面节奏。用于需要细致视觉分镜的视频分析。
license: MIT
metadata:
  video-server-display-name: 视觉分镜
  video-server-default-prompt: 重点分析构图、景别、运镜、转场、色彩和画面节奏，形成细致的视觉分镜说明。
  video-server-order: "30"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
---
# 视觉分镜分析

优先识别真实 Cut，并详细描述每个镜头的主体位置、构图层次、景别、摄影机运动、转场关系、光线、色彩和视觉节奏。保持时间线完整，所有结论需能从代表帧或相邻镜头关系中验证。
