---
name: screenplay-analysis
description: 分析完整剧本的结构、人物、场景、节奏、对白与可执行修改建议。用于中文或英文剧本的证据优先综合审阅。
license: MIT
metadata:
  video-server-display-name: 剧本综合分析
  video-server-default-prompt: 重点分析故事结构、人物弧光、场景功能、节奏与对白，并按优先级给出修改建议。
  video-server-order: "60"
  video-server-input-kinds: screenplay
  video-server-output-contract: screenplay-analysis
  video-server-references: references/evidence-rules.md
---

# 剧本综合分析

分析完整的规范化剧本，使用输入已有的源场景 ID 作为唯一证据坐标。先理解全局故事，再完成 logline、synopsis、结构、人物、逐场景、对白、优点和优先修改项。

## 工作规则

1. 区分文本事实、合理诊断和未知信息，不补写剧本中不存在的情节或创作背景。
2. 每个结构转折、人物结论、对白发现、优点和修改项必须绑定至少一个有效源场景 ID。
3. 人物分析覆盖外部目标、阻力、关键选择与变化；静态人物也要说明其稳定立场如何影响故事。
4. 场景分析说明功能、冲突、转变和节奏，不把地点变化自动当作戏剧转折。
5. 修改建议按叙事影响和可执行性排序，指出要解决的问题与受影响场景，不代写未经请求的新剧情。
6. 严格生成 `screenplay-analysis` 结果契约要求的字段，输出语言服从任务参数。

详细证据与诊断规则见 [evidence-rules](references/evidence-rules.md)。
