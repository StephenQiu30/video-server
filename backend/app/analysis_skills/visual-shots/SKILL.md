---
name: visual-shots
description: 把视频整理为可复核、可交接的分镜表，覆盖镜头起止状态、主体动作、构图、光色、转场、连续性和制作提示。
license: MIT
metadata:
  video-server-display-name: 分镜表制作
  video-server-default-prompt: 按真实 Cut 制作专业分镜表，逐镜记录起止状态、主体动作、构图、机位与运动、光色、转场、连续性锚点和镜头功能。
  video-server-order: "30"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/storyboard-table.md
---
# 分镜表制作

输出的是基于成片观察的“反向分镜表”，不是按固定秒数抽样的截图清单，也不是已经创建的生产镜头。每一行必须让导演、剪辑或生成团队在不回看片段的情况下，理解画面起点、动作变化、结束状态和相邻镜头的衔接约束。

## 核心要求

1. 全片初扫后复核真实 Cut；每镜至少比较起始、代表和结束画面。低对比转场、遮挡切换、屏幕内容更新和同镜头内状态变化都要人工语义复核。
2. `description` 使用统一四段格式；`narrative_function` 说明镜头任务及其衔接；`visual_tags` 承载角度、构图、光色和连续性等可排序维度。
3. 同一动作跨 Cut 时，上一镜的结束状态应能与下一镜的开始状态对上；无法对上时明确标为连续性风险，而不是虚构缺失动作。
4. `assets` 合并同一视觉身份，`highlights` 只保留值得重点复刻或审阅的候选；两者均引用真实镜头。
5. 视觉观察不能替代剧本、对白或音频事实。字幕和画面文字只能作为可见元素记录。

字段格式、标签词表、连续性检查和验收规则见 `references/storyboard-table.md`。最终只返回 `video-visual-analysis` Schema 所需字段。
