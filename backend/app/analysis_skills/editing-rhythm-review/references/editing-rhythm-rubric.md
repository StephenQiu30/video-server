# 剪辑节奏量表

## 一、逐镜标签

- 停留：`pace:readable-hold`、`pace:underheld`、`pace:overheld`。
- 切点：`cut:action`、`cut:reveal`、`cut:spatial`、`cut:beat`、`cut:unclear`。
- 信息密度：`density:sparse`、`density:balanced`、`density:overload`。
- 视觉连续：`motion:carry`、`motion:reset`、`attention:guided`、`attention:competing`。
- 边界：`boundary:edit`、`boundary:continuous-beat`、`boundary:uncertain`。它描述证据类型，不把连续节拍计作物理 Cut。

标签只在可见证据成立时使用；同一镜头可同时具有必要长停留和高信息密度，不能用一个标签替代描述。

## 二、判断规则

1. 阅读文字、理解界面操作、识别空间或观察状态变化所需的停留有明确用途。
2. 画面没有新增动作、信息、构图或情绪状态时，长停留才可能构成拖延。
3. 快切若持续提供清晰的动作或空间承接，可以有效；切换频繁但注意力锚点不断重置时才构成无目的快切风险。
4. 信息过载关注同一时刻竞争的主体、文字、运动和界面变化，不用镜头数量替代判断。
5. 节奏建议优先保护理解，再讨论速度；不得把所有问题都归结为“剪短”。
6. 连续长镜头应按有意义的任务阶段判断内部停留与推进；只有阶段重置时使用 `transition_in=continuous`，不能按固定秒数切片或把持续运镜本身视为新节拍。

## 三、交付自检

- 全片镜头和场景覆盖完整。
- 结论同时考虑停留、切点、信息密度和段落变化。
- 建议引用真实 `shot.id`，并说明修订后应改善的可读性或推进效果。
- 未使用音频、平台指标或固定行业阈值冒充当前成片证据。
- 物理剪辑频率与连续镜头内部节拍分别描述；超过 10 秒仍为单项时已用 `segmentation:single-unit-verified` 记录完整复核。
