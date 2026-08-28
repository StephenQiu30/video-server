---
name: scene-extraction
description: 把连续镜头归并为可复核的场景段落，提炼空间、主体事件、叙事任务、视觉规则和连续性风险。用于场景拆解与复用准备。
license: MIT
metadata:
  video-server-display-name: 场景提炼
  video-server-default-prompt: 在真实逐镜头结果之上提炼场景段落，逐场说明空间、主体与事件、叙事任务、视觉规则、进出场依据和连续性风险。
  video-server-order: "35"
  video-server-input-kinds: video
  video-server-output-contract: video-visual-analysis
  video-server-references: references/scene-boundaries.md
---
# 场景提炼

目标是把逐镜头时间线提升为可用于剧本回溯、场景资产整理和后续制作的场景段落。场景不是单个 Cut、固定时长分段或地点资产的别名，而是一组在稳定时空和连续事件中共同完成同一主要任务的相邻镜头。

## 执行原则

1. 先完成真实 Cut 级 `shots`，再自下而上归并 `scenes`；不得先猜场景再强迫镜头服从。
2. 场景边界必须有至少一种可见依据：空间切换、时间状态重置、主体/事件目标改变、视觉规则明显重置或段落进出场完成。
3. 每个镜头必须且只能属于一个场景；场景按时间顺序连续覆盖全部镜头，不允许跨越无关镜头合并同一地点。
4. 同一地点不一定是同一场景；交叉剪辑回到同一地点时，应按连续时间段建立新场景并在描述中说明呼应关系。
5. `location` 只写可见空间身份；无法确认真实地名、时间或人物关系时使用保守描述。

## 交付重点

- `description` 概括场景中的主体、事件推进、开始状态和结束状态。
- `narrative_function` 说明该场景在全片中的主要任务及进入/退出依据。
- `visual_rules` 提炼场景内稳定可复用的构图、光色、机位、运动和关键资产约束。
- `continuity_risks` 只记录具体可检查的问题；没有明确风险时返回空数组。
- 场景、高光和资产都是候选信息，不代表已创建项目场景或完成主选。

边界判定、字段写法和验收规则见 `references/scene-boundaries.md`。最终只返回 `video-visual-analysis` Schema。
