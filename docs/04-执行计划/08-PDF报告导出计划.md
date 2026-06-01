---
layer: plan
doc_no: LP-2026-06-02-PDF
audience:
  - Dev
  - QA
purpose: "实现 PDF 报告导出能力"
owner: StephenQiu30
inputs:
  - "docs/02-产品需求/05-AI摘要与PDF报告.md"
  - "docs/02-产品需求/03-MVP需求清单.md"
downstream:
  - "docs/05-测试验收/01-验收标准.md"
---

# PDF 报告导出计划

## 1. 目标

实现下载任务的 PDF 报告导出能力，将视频元数据、AI 摘要和思维导图整合为可下载的 PDF 文件。

### 1.1 TDD 要求

本计划采用测试驱动开发，必须覆盖以下场景：

| 场景 | 测试内容 | 验证方式 |
| --- | --- | --- |
| 权限验证 | 只能导出自己任务的 PDF | 跨用户访问返回 403 |
| 任务状态 | 只有完成的任务可导出 | 未完成任务返回 400 |
| 响应头 | PDF 文件正确下载 | Content-Type 和 Content-Disposition 正确 |
| 内容完整性 | PDF 包含必要信息 | 验证 PDF 内容 |
| AI 摘要有无 | 有无 AI 摘要都能生成 | 两种场景都成功 |

### 1.2 验证命令

```bash
pytest apps/api/tests/test_finalize_features.py -q
```

## 2. 任务拆解

### 2.1 PDF 服务层

- [ ] 2.1.1 定义 PDF 服务接口
  - `generate_report(task_id: str, include_ai: bool = True) -> bytes`
  - 返回 PDF 文件字节流

- [ ] 2.1.2 实现 PDF 模板引擎
  - 封面页模板
  - 视频信息页模板
  - AI 摘要页模板（条件渲染）
  - 思维导图页模板（条件渲染）
  - 下载记录页模板

- [ ] 2.1.3 实现 Mermaid 渲染
  - 服务端渲染 Mermaid 为图片
  - 支持 mindmap 语法
  - 处理渲染失败降级

- [ ] 2.1.4 实现 PDF 生成
  - 使用 reportlab 或 weasyprint
  - 支持中文字体
  - 处理分页和布局

### 2.2 API 接口层

- [ ] 2.2.1 实现 PDF 导出接口
  - `GET /api/tasks/{task_id}/report/pdf`
  - 权限验证：只能导出自己的任务
  - 状态验证：任务必须已完成
  - 返回 PDF 文件流

- [ ] 2.2.2 实现 PDF 预览接口（可选）
  - `GET /api/tasks/{task_id}/report/preview`
  - 返回 HTML 预览

- [ ] 2.2.3 实现批量导出接口（可选）
  - `POST /api/tasks/batch/report/pdf`
  - 支持多任务合并导出

### 2.3 缓存层

- [ ] 2.3.1 实现 PDF 缓存
  - 缓存已生成的 PDF 文件
  - 缓存键：task_id + include_ai
  - 缓存过期策略

- [ ] 2.3.2 实现缓存失效
  - AI 分析完成时清除缓存
  - 任务状态变更时清除缓存

### 2.4 测试层

- [ ] 2.4.1 单元测试：PDF 服务
  - 测试 PDF 生成
  - 测试模板渲染
  - 测试 Mermaid 渲染

- [ ] 2.4.2 集成测试：API 接口
  - 测试权限验证
  - 测试状态验证
  - 测试响应头

- [ ] 2.4.3 端到端测试：完整流程
  - 测试下载 -> AI 分析 -> PDF 导出
  - 测试无 AI 摘要的 PDF 导出

## 3. 验收条件

### 3.1 功能验收

| 验收项 | 验证方式 | 预期结果 |
| --- | --- | --- |
| 有 AI 摘要的 PDF | 导出已完成任务的 PDF | PDF 包含视频信息、摘要和思维导图 |
| 无 AI 摘要的 PDF | 导出无 AI 分析任务的 PDF | PDF 包含视频信息，无摘要部分 |
| 权限控制 | 尝试导出他人任务 | 返回 403 Forbidden |
| 状态检查 | 尝试导出未完成任务 | 返回 400 Bad Request |
| 文件下载 | 浏览器下载 PDF | 文件名正确，可正常打开 |

### 3.2 边界验收

| 边界场景 | 验证方式 | 预期结果 |
| --- | --- | --- |
| 大文件处理 | 导出大视频的 PDF | 正常生成，不超时 |
| 并发导出 | 多个请求同时导出 | 各自独立处理 |
| 缓存命中 | 重复导出同一任务 | 快速返回缓存 |
| Mermaid 渲染失败 | 无效 Mermaid 语法 | 降级为文本展示 |

### 3.3 TDD 验收

```bash
# 运行 PDF 相关测试
pytest apps/api/tests/test_finalize_features.py -q

# 预期输出
# test_pdf_export_with_ai_summary PASSED
# test_pdf_export_without_ai_summary PASSED
# test_pdf_export_permission_denied PASSED
# test_pdf_export_task_not_completed PASSED
# test_pdf_response_headers PASSED
# test_pdf_content_integrity PASSED
# ... (更多测试用例)
```

## 4. 依赖关系

| 依赖 | 说明 | 状态 |
| --- | --- | --- |
| 视频下载成功 | PDF 导出的前提条件 | 已完成 |
| AI 分析结果 | 可选依赖 | 待实现（STE-60） |
| PDF 生成库 | reportlab 或 weasyprint | 待安装 |
| Mermaid 渲染 | 服务端渲染能力 | 待实现 |

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| PDF 生成失败 | 无法导出报告 | 返回可理解的错误信息 |
| 中文乱码 | PDF 内容不可读 | 使用支持中文的字体 |
| Mermaid 渲染失败 | 思维导图缺失 | 降级为文本展示 |
| 文件过大 | 下载超时 | 限制内容长度，分页处理 |

## 6. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 初始化文档 |
