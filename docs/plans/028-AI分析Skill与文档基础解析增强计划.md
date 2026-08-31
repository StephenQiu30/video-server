# 028 AI 分析 Skill 与文档基础解析增强计划

- 状态：Implementation complete / Provider canary pending
- 日期：2026-08-31
- 对应设计：`docs/design/028-AI分析Skill与文档基础解析增强设计.md`
- 对应验收：`docs/acceptance/028-AI分析Skill与文档基础解析增强验收.md`

## 1. 调研与边界

- [x] 复读 55 项 AI 成片产线原文并对照当前 Skill 目录去重。
- [x] 选择成片叙事结构、剪辑节奏、连续性与成片 QA 三项分析能力。
- [x] 排除生成、剪辑执行、音频分析、运行时安装和通用文档问答。

## 2. Skill 实现

- [x] 增加三个 `SKILL.md` 与渐进式 reference。
- [x] 绑定 `video + video-visual-analysis`，保持动态目录和前端零硬编码。
- [x] 更新供应链 NOTICE、目录顺序、引用编译和行为边界测试。
- [ ] 使用受控视频分别完成三个 Skill 的真实 Provider canary 与人工质量复核。

## 3. 文档解析

- [x] 增加确定性 `DocumentParseSummary`。
- [x] DOCX 保留标题与列表 Markdown，统计表格；PDF 返回安全解析后的页数。
- [x] 把 summary 保存到 normalized Artifact metadata，并通过详情 API/OpenAPI 公开。
- [x] 前端增加“基础解析”摘要与 fixture/test。

## 4. 验证

- [x] skill-creator quick validation 与项目 Registry 测试。
- [x] 文档 Domain/Verifier/API/Repository 定向测试。
- [x] 后端 Ruff 与 MyPy。
- [x] 前端文档详情测试与 TypeScript。
- [x] 前端全量 lint/format、207 项测试与 production build。
- [ ] 后端全量 Pytest：本次 1,348 passed、1 skipped；唯一失败为并行工作区 `SITE_URL` Compose 白名单未同步，与 028 无关。
- [ ] 真实 Provider canary。
