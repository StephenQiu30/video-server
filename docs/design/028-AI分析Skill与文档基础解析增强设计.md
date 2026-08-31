# 028 AI 分析 Skill 与文档基础解析增强设计

- 状态：Implemented / Provider validation pending
- 日期：2026-08-31
- 对应需求：`docs/prd/028-AI分析Skill与文档基础解析增强需求.md`

## 1. 分析能力设计

三个 Skill 复用 `AnalysisSkillRegistry → BuiltinAnalysisSkillCatalog → Analysis Worker` 当前链路。前端只消费动态目录，不新增 skill ID 条件分支。

| Skill | 主要诊断问题 | 结果映射 |
| --- | --- | --- |
| `narrative-structure-review` | 建立、推进、转折、兑现、重复和跳步 | `shots.narrative_function`、`scenes`、`production_advice` |
| `editing-rhythm-review` | 停留、信息密度、切点动机、视觉节奏变化 | `shots.visual_tags`、`scenes`、`production_advice` |
| `continuity-quality-review` | 主体/资产状态、空间动作、图形文字和可见技术瑕疵 | `scenes.visual_rules/continuity_risks`、`production_advice` |

三项都先生成完整 Cut 级时间线，再做专项判断；Skill 只改变分析重点，不改变视频输入权限、模型工具、结果 Schema 或发布路径。

## 2. 文档解析模型

领域新增不可变 `DocumentParseSummary`：

```text
page_count: int | null
paragraph_count: int
heading_count: int
list_item_count: int
table_count: int
dialogue_block_count: int
```

`normalized_document()` 在 canonical UTF-8/LF 文本和 `ScreenplayScene.elements` 生成后确定性计算计数。DOCX verifier 额外提供表格数，PDF verifier 提供已校验页数；正文、标题、人物名和对白不复制到 summary。

summary 随 normalized Artifact 的 `artifact_metadata.parse_summary` 保存。详情 repository 只在已经 owner scoped 的 normalized Artifact 查询中严格读取六个 allowlist 字段；字段缺失时公开 `null`，类型或范围非法时按内部损坏处理。列表仍不关联 Artifact，因此不增加正文或对象存储读取。

## 3. DOCX 与 PDF

- DOCX 在完成 ZIP/OPC 安全校验后读取正文。段落 style ID/name 匹配 Heading 1–6 时增加同级 `#` 前缀；List Bullet/Number 增加 `-`/`1.` 前缀。普通文本不改变，表格行继续用 Tab 分隔，以保留现有两列人物/对白解析。
- PDF 继续 strict 解析、活动内容检查、页数/content stream/文字质量门禁；页数作为 metadata 返回，页面正文仍以空行连接，避免向模型输入添加伪场景或页码。

## 4. API 与界面

`DocumentDetailResponse` 新增必需但可空的 `parse_summary`。ready 新文档返回对象，上传/解析/失败状态返回 `null`。前端文档信息区增加“基础解析”二级摘要；`page_count=null` 显示“源格式不提供”，其他计数使用真实零值，不显示为等待解析。

DOCX 规范化标题会被现有安全 Markdown renderer 和目录提取器直接消费；不允许 HTML、链接跳转或脚本执行。

## 5. 安全与兼容

- 不新增依赖、SQL schema、网络或文件权限。
- Artifact metadata 只保存低敏整数；API 不返回 object key、SHA-256 或正文副本。
- 现有 ready Artifact 没有 summary 时返回 `null`，不回读全文推断，也不迁移或改写不可变文档。
- 真实 Provider 质量验证独立于静态目录完成状态；失败不影响已有视频与文档能力。
