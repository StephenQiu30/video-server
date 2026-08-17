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

优先识别真实 Cut，并详细描述每个镜头的主体位置、构图层次、景别、摄影机运动、转场关系、光线、色彩和视觉节奏。结果是当前项目的视觉镜头候选说明，不是已经确认的分镜资产、生成 Prompt 或主选结果。保持时间线完整，所有结论需能从代表帧或相邻镜头关系中验证。

## 项目生产映射

- `shots` 只表达可见的镜头事实和视觉语言；不要把镜头建议写成“已创建镜头”。
- `assets` 只表达画面中可复用的视觉身份，并用证据镜头合并同一对象；不要虚构资产版本、角色状态 ID 或项目资源。
- `highlights` 是需要比较或优先复刻的候选，`production_advice` 是建议；两者都不等于用户的最终选择。
- 视觉观察不能替代剧本事实、对白事实或音频分析。字幕和画面文字只能作为可见文字描述。

最终只输出当前 `video-visual-analysis` Schema 所需字段，不返回额外的生产对象、Markdown 或解释。
