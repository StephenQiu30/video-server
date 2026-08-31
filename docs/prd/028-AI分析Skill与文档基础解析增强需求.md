# 028 AI 分析 Skill 与文档基础解析增强需求

- 状态：Implemented / Provider validation pending
- 日期：2026-08-31
- 对应设计：`docs/design/028-AI分析Skill与文档基础解析增强设计.md`
- 对应调研：`docs/research/017-Agent视频Skill与成片分析能力调研.md`

## 1. 目标

1. 把成片叙事结构、剪辑节奏、连续性与成片 QA 作为独立内置 Skill 提供给视频分析。
2. 保持现有严格时间轴、分镜证据、结果契约、Provider、报告与任务生命周期。
3. 让用户在上传文档详情中看到基础解析统计，并让 DOCX 标题/列表进入规范化 Markdown。

## 2. 功能需求

### FR-028-01 分析 Skill

- 目录新增 `narrative-structure-review`、`editing-rhythm-review`、`continuity-quality-review`。
- 三项只接受 `video`，只返回 `video-visual-analysis`，并自动通过现有 `/api/analysis-skills` 和前端配置器展示。
- 分析仍完整覆盖全片 `shots/scenes`；摘要、高光与制作建议引用真实 `shot.id`。
- 没有可靠音频证据时不得评价对白、语速、音乐、音效或声音同步；不得预测留存、完播、点击或转化。

### FR-028-02 Skill 安全

- Skill 只包含 `SKILL.md` 和一层显式 reference，不包含脚本、工具、网络、插件、MCP、资产或子 Agent。
- 目录加载、引用路径、输入类型和结果契约继续 fail closed；指令 SHA-256 进入任务快照。

### FR-028-03 文档基础解析

- DOCX 保留 Heading 1–6 与有序/无序列表的安全 Markdown 语义；表格正文继续以受控文本进入现有剧本结构解析。
- PDF 成功解析后返回页数；文本格式页数为空，不伪造分页。
- 统一产生文本段、标题、列表项、表格、对白块计数并保存在 normalized Artifact metadata。
- 文档详情 API 返回可空 `parse_summary`；前端以“基础解析”展示，不把统计解释为质量评分。

## 3. 非目标

- 不新增视频生成、自动剪辑、ComfyUI、Remotion、数字人或多模型生成编排。
- 不新增音频分析、逐帧编码检测、自动修复或发布审批。
- 不新增 OCR、PPTX/XLSX/EPUB、通用文档问答、向量检索或多文件分析。
- 不新增结果契约、数据库表或运行时第三方 Skill 安装。

## 4. 验收标准

- 三项 Skill 的顺序、引用编译、边界文本与结果契约测试通过。
- DOCX 标题/列表、DOCX 表格、两页 PDF、Markdown/TXT/Fountain 均产生稳定解析摘要。
- API/OpenAPI/前端显示 `parse_summary`，pending/failed 与不提供页数的格式安全显示。
- 后端 Ruff/MyPy/Pytest 与前端 lint/typecheck/test/build 通过；真实 Provider canary 未通过前不得宣称视觉质量已完成验证。
