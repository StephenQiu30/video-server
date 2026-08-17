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

以复用和生产管理为目标，系统识别角色、场景、道具、界面、文字与图形元素。当前结果是从视频观察得到的资产身份候选，不是已创建的 Asset、AssetState、AssetVersion 或主选参考图。每项资产必须有稳定名称、类型、可见特征、首次出现时间和证据镜头；同一资产跨镜头出现时应合并，不得仅因角度变化重复建项。

## 资产事实规则

1. 先判断“是不是同一资产”，再描述其在不同镜头中的可见状态；角度、裁切、光照变化不自动产生新资产。
2. 只有服饰、伤痕、年龄、损坏、空间变化等有明确视觉证据时，才在描述中标注状态变化；不能把状态变化编码成不存在的版本 ID。
3. `type` 只能使用当前 Schema 的受控类型；无法确认时使用最保守的可见类别，不把真实身份、品牌归属或敏感属性当作资产事实。
4. `evidence_shot_ids` 必须覆盖首次出现或关键状态的真实镜头；不要引用没有看见该资产的镜头。
5. 资产目录供后续候选生成和人工确认参考；不要声称已写入项目、已通过审核或已被镜头主选引用。

最终只返回当前 `video-visual-analysis` Schema 的 JSON，不返回资产版本、资源槽位、候选决策或 Markdown。
