# Agent 视频 Skill 与成片分析能力调研

- 日期：2026-08-31
- 状态：调研完成
- 关联需求：`docs/prd/028-AI分析Skill与文档基础解析增强需求.md`

## 1. 原文结论

[《我扒完了 GitHub 上 55 个 AI 成片产线，得出一个结论》](https://x.com/servasyy_ai/status/2092059961656537546)把项目分为三类：装入 Claude Code/Codex 的视频 Skill、一站式成片平台、分镜/导演画布，并额外列出 ComfyUI 控制、可复现生成 runtime、视频合成和看片自检等底座。

对本项目最重要的不是接入更多生成模型，而是以下三个信号：

1. 28/55 项目把能力包装为 Agent Skill，说明窄能力、可发现目录和渐进式说明已经成为有效交付形态。
2. 主要竞争发生在“剧本 → 分镜 → 生成 → 合成 → 自检”的编排层，不在单一模型。
3. `watch-skill`、`video-production-skills` 与 `video-shotcraft` 都把渲染后复看、开场、画面文字、连续性和 QA 当作独立环节，而不是综合 Prompt 中的一句附带要求。

## 2. 与现有能力的重叠

项目已经有导演拉片、综合分析、分镜表、场景提炼、高光、开场钩子、资产目录、视频转文章和三项剧本 Skill。角色/场景/道具拆分、分镜、开场和文章化不应重复建设；生成、剪辑执行、ComfyUI、Remotion、数字人、多模型费用路由也超出当前“下载与分析”产品边界。

真正缺少的是三个可单独选择、可复核的成片诊断视角：

- 成片叙事结构：从可见段落判断建立、推进、转折、兑现、重复与跳步。
- 剪辑节奏：判断镜头停留、信息密度、切点动机和视觉节奏变化，不把更多 Cut 当作更好。
- 连续性与成片 QA：对主体状态、空间方向、动作、图形文字和明显技术瑕疵做交付前审查。

这三项共享现有 `video-visual-analysis` 结果契约即可表达：逐镜事实进入 `shots`，段落判断进入 `scenes`，成立候选进入 `highlights`，修订项进入 `production_advice`。不需要新增模型 Schema、数据库枚举或前端硬编码。

## 3. Skill 供应链决策

新增 Skill 是项目特定的原创重写，只采用已经在 `backend/app/analysis_skills/NOTICE.md` 固定审查的分析原则：

- [watch-skill](https://github.com/oxbshw/watch-skill)：看片自检、观察与结果区分；不引入 OCR/ASR、索引、服务和评分公式。
- [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)：渲染后复核、文字可读性、镜头交接；不引入镜头卡、媒体、模板和生成工作流。
- [DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)：节拍、调度、镜头动机和 QC 思维；不引入完整制作流程和风格模仿。

每项只包含 `SKILL.md` 和一个显式 allowlist 的 Markdown reference；不包含脚本、MCP、网络、插件、外部资源或跨 Skill 自动调用。任务创建时继续保存编译指令与 SHA-256。

## 4. 上传文档解析差距

现有 DOCX 只抽取段落纯文本，丢失标题和列表样式；PDF 能提取正文但没有把权威页数返回给用户；详情只展示场景数与字符数，用户无法快速判断基础结构是否被正确识别。

本次采用以下最小增强：

1. DOCX 的 Heading 1–6 转成同级安全 Markdown 标题，List Bullet/Number 转成 Markdown 列表；普通段落和表格中的制表符文本保持现有剧本分析语义。
2. PDF 在安全解析完成后保留页数统计，不向规范化正文注入页码标记。
3. 对规范化文本确定性统计文本段、标题、列表项、表格和对白块；只存低敏计数，不把标题、人物或对白正文复制到元数据。
4. 解析摘要随 normalized Artifact metadata 持久化，只在 owner-scoped 文档详情中公开；列表不额外读取正文或 Artifact。

## 5. 发布边界

- 三项新 Skill 的静态目录、引用编译、契约和边界测试通过后可进入目录，但真实视觉质量仍需受控视频 Provider canary。
- 文档解析仍只接受 DOCX、可提取文本的 PDF、UTF-8 TXT/Markdown/Fountain；不新增 OCR、PPTX、XLSX、EPUB 或通用文档问答。
- 解析摘要是确定性结构统计，不代表内容质量评分，也不能改变剧本分析结果契约。
