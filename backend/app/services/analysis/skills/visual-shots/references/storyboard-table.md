# 分镜表字段规范

## 一、每镜观察点

每个镜头至少核对三帧：

- **起始帧**：物理转场完成后的第一个稳定画面，或连续节拍新阶段开始时能证明任务已经重置的画面，确定主体、空间和动作起点。
- **代表帧**：最能表达镜头构图与叙事任务的画面，时间写入 `representative_frame_ms`。
- **结束帧**：切出前的最后稳定状态，记录动作、道具、朝向和光线状态。

代表帧不能代替起止帧。若连续长镜头内出现已经完成的屏幕状态、主体任务、空间区域、动作阶段或构图任务重置，应拆成新的分析分镜；若变化只是同一任务的连续过程，则在描述中写出过程。不得只凭持续运镜或固定秒数拆分。

## 二、分镜行映射

虽然 JSON 没有表格列名，每个 `shot` 必须能恢复以下分镜信息：

| 分镜信息 | 输出位置 | 写法 |
|---|---|---|
| 镜号与时码 | `index/start_ms/end_ms` | 连续、无间隙、无重叠 |
| 代表画面 | `representative_frame_ms` | 位于镜头区间内，优先核心构图而非转场残帧 |
| 主体与动作 | `description` 第 1 段 | 主体位置；开始 → 动作 → 结束状态 |
| 空间与构图 | `description` 第 2 段 | 前中后景、重心、负空间、遮挡、关键物位置 |
| 光线与色彩 | `description` 第 3 段 | 可见光向、明暗关系、主色/强调色，不猜设备参数 |
| 镜头起止 | `description` 第 4 段 | 起始状态 → 结束状态 |
| 景别/运动/边界 | 受控字段 | 编辑转场写实际类型；无编辑的新阶段写 `continuous`；类型不明写 `unknown` |
| 镜头任务 | `narrative_function` | 节拍 + 与相邻镜头衔接 + 可见依据 |
| 视觉/连续性 | `visual_tags` | 使用下述受控前缀 |

`description` 推荐句式：`主体与动作：……；空间与构图：……；光线与色彩：……；镜头状态：…… → ……`。

## 三、受控标签

标签使用 `维度:值`，每个维度只保留能从画面确认的值：

- `angle:` eye-level / high / low / overhead / dutch / pov / over-shoulder / unknown
- `composition:` centered / rule-thirds / symmetry / leading-lines / frame-within-frame / negative-space / layered / silhouette
- `lighting:` high-key / low-key / side / back / rim / practical / soft / hard / mixed
- `palette:` warm / cool / neutral / monochrome / complementary / accent-color
- `continuity:` screen-direction / eyeline / action / prop-state / costume / lighting / geography / text-state
- `rhythm:` hold / reveal / acceleration / deceleration / interruption / montage
- `segmentation:` single-unit-verified（仅用于超过 10 秒且完整复核后仍确认为单一分析分镜的素材）

标签是检索维度，不是散文。不要写 `cinematic`、`beautiful`、`高级感` 等不可复核词。

## 四、连续性检查

逐列扫描全部镜头：

1. **空间**：建立镜头是否让人物和关键物的相对位置可理解。
2. **方向**：人物视线、移动方向和画面进出方向是否在相邻镜头可衔接。
3. **动作**：上镜结束动作是否与下镜开始动作一致；跳跃是有意省略还是证据不足。
4. **状态**：道具手别/位置、服装、屏幕文字、门窗开合、破损和光线是否稳定。
5. **构图变化**：景别、角度或运动变化是否为节拍服务；不要机械套用 30 度或 180 度规则。
6. **边界核对**：物理 Cut、连续节拍和未知边界是否被准确区分；不能把“没看到 Cut”当作没有阶段变化。
7. **时长核对**：分镜区间必须准确相加到权威总时长。

## 五、制作建议

`production_advice` 应给出反向复刻方法而非泛泛评价：优先镜头、必须锁定的连续性锚点、建议拆分的复杂动作、适合固定帧控制的起止状态，以及明确验收条件。
