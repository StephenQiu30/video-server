---
name: highlights
description: 识别最有传播力、信息密度或情绪价值的片段并解释依据。用于提炼视频高光与传播素材。
license: MIT
metadata:
  video-server-display-name: 高光提炼
  video-server-default-prompt: 重点识别高传播力、高信息密度或高情绪价值的片段，并说明选择依据和适用场景。
  video-server-order: "40"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
---
# 高光片段提炼

完整观察视频后，优先发现具有强视觉冲击、关键信息、情绪转折或传播潜力的镜头组合。高光在当前项目中是可比较、可复核的候选，不是自动主选、营销结论或已经发布的素材。高光必须给出精确时间范围、1 至 5 分评分、选择理由和证据镜头；不得只凭台词或标题判断。

## 候选与决策边界

1. 只有真正不同的视觉、信息或情绪价值才建立独立高光；不要为了凑数量拆分同一段，也不要把所有镜头都标为高光。
2. `score` 只表达本次观察中的相对优先级，不代表播放量、转化率或用户偏好。
3. `evidence_shot_ids` 必须是高光时间范围内的真实镜头 ID；高光范围不能超出权威时长。
4. `production_advice` 可以建议哪些候选适合复刻或继续比较，但不得声称已经选中、生成、审核或导出。
5. 视频画面无法证明的对白、音乐、音效、人物身份或传播结果不得作为高光理由。

最终只返回当前 `video-visual-analysis` Schema 的 JSON，不返回 Markdown、链接或额外候选状态字段。
