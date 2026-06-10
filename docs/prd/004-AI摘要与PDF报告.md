---
layer: PRD
doc_no: "004"
audience:
  - PM
  - Dev
  - QA
feature_area: ai-summary-pdf-report
purpose: "定义下载成功后的 AI 摘要、思维导图和 PDF 报告增强能力边界。"
canonical_path: "docs/prd/004-AI摘要与PDF报告.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/003-下载任务与产物归档.md"
  - "apps/worker/worker/ai_pipeline.py"
  - "apps/api/app/services/pdf.py"
outputs:
  - "AI 增强与 PDF 报告需求"
triggers:
  - "调整 AI provider"
  - "调整 PDF 导出"
  - "改变下载后增强产物策略"
downstream:
  - "docs/plans/004-01-AI摘要与思维导图计划.md"
  - "docs/plans/004-02-PDF报告导出计划.md"
  - "docs/plans/001-万能视频下载器MVP执行计划.md"
  - "docs/acceptance/001-万能视频下载器MVP测试计划.md"
---

# AI 摘要与 PDF 报告 PRD

## 1. 背景

用户选择方案 B 后，下载器不仅保存视频，还要完成内容整理闭环。当前系统已有 AI 转录、摘要、Mermaid 思维导图和 PDF 导出基础。本需求定义这些增强能力与主下载链路的关系。

## 2. 目标

1. 下载成功后，系统可异步提取音频、转录文本、生成摘要和思维导图。
2. 用户可在任务完成后导出 PDF 报告。
3. AI 失败不影响主视频下载结果，但必须记录状态和错误原因。

```gherkin
Given 下载任务已成功保存主视频
When AI 配置可用
Then Worker 异步生成摘要和思维导图
And 用户可以导出 PDF 报告
And AI 失败时任务仍保持下载成功
```

## 3. 非目标

- 不承诺所有语言、所有音质都能正确转录。
- 不把 AI 结果作为下载成功的必要条件。
- 不在没有 API key 时阻断下载。
- 不做多人协作文档编辑或报告模板商城。

## 4. 核心用户故事

| 用户 | 场景 | 验收标准 |
| --- | --- | --- |
| 学习用户 | 下载课程或讲座 | 可获得摘要、关键点和 PDF 报告 |
| 内容创作者 | 整理素材 | 可查看视频内容概要和结构化思维导图 |
| 自部署用户 | 未配置 AI Key | 视频下载成功，AI 状态为跳过 |

## 5. 状态模型

| 状态 | 含义 |
| --- | --- |
| `skipped` | 未配置 AI 或不满足处理条件 |
| `processing` | 正在转录、摘要或生成思维导图 |
| `completed` | AI 增强产物生成成功 |
| `failed` | AI 增强失败，主视频仍成功 |

## 6. 数据与权限边界

- AI 处理只在任务所属用户可见范围内保存结果。
- PDF 导出必须验证任务归属。
- 外部 AI provider 的 API key 只从服务端环境读取。
- AI 错误信息应避免泄露密钥、完整 URL 或敏感请求体。

## 7. 首版验收门禁

- 未配置 AI key 时任务显示 `skipped`。
- AI 成功时保存 `ai_summary` 和 `ai_mindmap`。
- AI 失败时保存 `ai_status=failed` 和可读错误。
- PDF 端点只允许任务完成后导出，并返回 PDF 二进制。

## 8. 风险与边界

AI provider 成本、速率限制和内容安全策略会影响增强能力。首版将 AI 作为可选增强，不纳入主下载 SLA。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 初始化 AI 摘要与 PDF 报告 PRD |
