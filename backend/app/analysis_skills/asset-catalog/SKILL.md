---
name: asset-catalog
description: 建立角色、场景、道具、界面、文字和图形元素清单。用于需要可复用视觉资产目录的视频分析。
license: MIT
metadata:
  video-server-display-name: 资产目录
  video-server-default-prompt: 重点建立角色、场景、道具、界面、文字和图形元素目录，并标注首次出现时间及证据镜头。
  video-server-order: "50"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
---
# 视觉资产目录

以复用和生产管理为目标，系统识别角色、场景、道具、界面、文字与图形元素。每项资产必须有稳定名称、类型、可见特征、首次出现时间和证据镜头；同一资产跨镜头出现时应合并，不得仅因角度变化重复建项。
