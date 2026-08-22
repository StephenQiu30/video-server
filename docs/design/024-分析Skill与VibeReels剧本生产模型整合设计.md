# 024 分析 Skill 与 VibeReels 剧本生产模型整合设计

> 设计日期：2026-08-17
> 参考项目：`/Users/stephenqiu/Desktop/StephenQiu/Lanverse`

## 1. 目标与边界

本设计把 Lanverse 中已经落地的剧本生产语义吸收到 Video Server 的分析 Skill，但不复制 Lanverse 的数据库、API 或媒体生产实现。

Video Server 当前仍然只有两类输入：视频和规范化剧本文档；当前分析结果包含 `video-visual-analysis`、`video-article`、`screenplay-analysis` 和 `screenplay-rewrite` 四类契约。因此 Skill 可以改进观察、文章化、证据、候选和建议的质量，但不能输出当前 Schema 没有承载能力的 Asset、ShotSelection、CoverageDecision、Version 或 ExportManifest 对象。

## 2. 从 VibeReels/Lanverse 吸收的核心语义

### 2.1 剧本不是一段摘要，而是生产事实来源

剧本分析应先识别可复用事实，再给出判断：

- 场景：标题、地点、时间、功能、冲突和转变；
- 对白：说话者、对白功能、关系/潜台词和覆盖问题；
- 资产线索：角色、地点、道具、服化、视觉风格和状态变化；
- 镜头线索：可视化动作、构图机会、转场、关键动作和高光候选；
- 连续性：时间、知识、道具、关系和行动后果是否闭合。

当前 `screenplay-analysis` 的映射如下：

| 生产事实 | 当前 Skill 字段 | 约束 |
| --- | --- | --- |
| 场景事实 | `scenes` | 一个源场景一条，按 `source_scene_id` 原顺序覆盖 |
| 主要角色事实 | `characters` | 只列有独立叙事作用的人物，必须有场景证据 |
| 对白问题 | `dialogue_findings` | 只写对白诊断，不伪造逐句对白数据库 |
| 连续性/结构问题 | `priority_revisions` | 给出可执行修改与受影响场景 |
| 镜头化线索 | 场景 `findings` 或结构建议 | 只作为线索，不创建 Shot 对象 |
| 地点/道具/服化线索 | 场景 `findings` 或人物/修改建议描述 | 不创建 Asset/AssetState 对象 |

### 2.2 候选、决策和最终对象分离

Lanverse 的抽取候选、人工决策和 coverage 报告是不同层次。Video Server 的 Skill 结果只能生成观察结论和候选建议：

- 视频 `highlights` 是高光候选，不是最终主选；
- 视频 `assets` 是可见资产候选，不是已创建的持久化资产；
- `production_advice` 是生成建议，不代表已提交 Provider 任务；
- 剧本 `priority_revisions` 是修改建议，不代表已修改原稿；
- `screenplay-rewrite` 是新文本版本候选，不覆盖原文，也不自动使下游对象失效。

### 2.3 证据和版本边界

- 视频证据使用服务端生成的 `shot.id` 和时间区间；
- 剧本证据使用规范化输入生成的 `source_scene_id`；
- 改写使用服务端绑定的 `source_sha256`、场景 ID 和 part 序号；
- Skill 不得使用模型自造的场景号、文件名、字符偏移或“上一块/下一块”作为证据坐标；
- 输入版本由父 Worker 锁定，后续用户修改不会改变正在执行的任务快照。

## 3. 全部内置 Skill 的职责划分

| Skill | 负责 | 不负责 |
| --- | --- | --- |
| `director-breakdown` | 全片真实 Cut、视觉事实、镜头价值、资产线索、制作建议 | 音频事实、资产创建、主选、生成任务 |
| `comprehensive` | 视频全局摘要、完整时间线、高光/资产/建议的平衡汇总 | 把建议写成已完成的生产状态 |
| `video-to-article` | 按主题重组视频内容，生成带时间证据的中文文章、核心观点和局限说明 | 逐句字幕导出、未经证实的对白/作者/日期/外部背景、文章发布 |
| `visual-shots` | 构图、景别、运镜、转场、光色和视觉节奏 | 剧本事实、对白事实、镜头持久化 |
| `highlights` | 可比较的高光候选和证据 | 自动选择、传播效果承诺、营销结论 |
| `asset-catalog` | 视觉资产身份、首次出现、跨镜合并和状态线索 | Asset/Version/Reference 的落库和审核 |
| `screenplay-analysis` | coverage：故事、人物、场景、对白、优点和修改 | 预算、拍摄 breakdown、资产/镜头创建 |
| `screenplay-structure-review` | 节拍、因果、转折、连续性、节奏和覆盖缺口 | 自动改稿、镜头生成、人工决策 |
| `screenplay-rewrite` | 有 glossary 和源哈希约束的文本版本改写 | 覆盖原稿、修改生产对象、自动发布版本 |

## 4. 长剧本执行约束

当前 Video Server 在超过单次容量时按完整源场景分块，并使用无 `scenes` 的汇总调用生成全局字段。Skill 必须遵守：

1. 分块结果只对本块可见事实负责；不能假装知道未提供的结局。
2. 分块 `scenes` 必须完整、唯一、有序地覆盖本块源场景。
3. 汇总只能使用已校验的分块 JSON；不能读取文件、访问网络或重新发明场景。
4. 父 Worker 最终按源顺序合并场景并再次验证证据；模型不能改变这个顺序。
5. 任何超出当前 Schema、资源上限或证据边界的要求都应被拒绝或降级为明确的未知，不以超长自由文本绕过限制。

## 5. 本期落地

- 全部 9 个内置 Skill 已写入上述项目生产边界；
- 新增 `video-to-article` 视频输入 Skill，复用现有视频制品、异步任务、报告持久化和 Markdown/DOCX 导出；
- 文章章节必须携带权威视频时间证据；当前受限视频执行器以视觉观察为主，没有可靠音频转写时必须在 `limitations` 中说明，不得编造对白或作者信息；
- `screenplay-analysis` 增加当前 JSON 契约、分块/汇总模式和字段映射说明；
- `screenplay-rewrite` 增加不可变版本、glossary 和下游生产对象隔离规则；
- Video Server 的 Prompt 继续负责安全边界、Schema 和输入信任边界，Skill 负责领域判断；
- 本期不新增数据库对象、API 字段或媒体生产能力。

如果后续要真正承接 Lanverse 的“场景/对白/资产/镜头候选 + 人工决策 + coverage”闭环，需要另立 `screenplay-extraction` 结果契约和版本化候选模型，不能继续把这些对象塞进现有 `screenplay-analysis` 字段。
