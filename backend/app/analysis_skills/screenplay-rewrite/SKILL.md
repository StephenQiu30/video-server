---
name: screenplay-rewrite
description: 执行中文和英文剧本的跨语言改写或同语言润色，并保持场景、人物、事实与术语一致。用于 zh-CN 和 en-US 剧本改写任务。
license: MIT
metadata:
  video-server-display-name: 剧本中英改写
  video-server-default-prompt: 在不改变情节事实和场景顺序的前提下完成中英文改写或同语言润色，并保持人物声音与术语一致。
  video-server-order: "80"
  video-server-input-kinds: screenplay
  video-server-output-contract: screenplay-rewrite
  video-server-references: references/rewrite-rules.md
---

# 剧本中英改写

按源场景顺序改写中文或英文剧本。目标语言由任务参数确定：目标与源语言不同时做忠实本地化，相同时做表达润色。不得改变故事事实、场景数量或角色身份。

## 工作规则

1. 保留源场景 ID、顺序、标题语义、角色名、动作因果和关键信息；不新增或删除剧情。
2. 先建立人名、地名、称谓、组织、专有物件和反复意象的 glossary，再在所有块中一致使用。
3. 对白应符合目标语言自然表达，同时保留人物声音、关系、潜台词、打断和情绪强度。
4. 每个 chunk 只对应一个源场景及连续 part，携带受控流程给出的源 SHA-256；不自行改写标识或哈希。
5. 所有源场景必须且只能覆盖一次，块按场景和 part 顺序返回；禁止返回另一份独立全文。
6. 严格生成 `screenplay-rewrite` 结果契约要求的 glossary、chunks 和 change summary，不输出工具调用或外部链接。

详细语言与完整性规则见 [rewrite-rules](references/rewrite-rules.md)。
