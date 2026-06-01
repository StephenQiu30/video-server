---
layer: PRD
doc_no: "005"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: self-hosted-cookie-compliance
purpose: "定义自部署浏览器 Cookie 配置、合规提示、限流、配额和滥用治理边界。"
canonical_path: "docs/prd/005-自部署Cookie与合规治理.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "AGENTS.md"
  - "README.md"
  - "apps/api/app/core/config.py"
  - "apps/worker/worker/download_runner.py"
outputs:
  - "自部署 Cookie 与合规治理需求"
triggers:
  - "开放登录态相关能力"
  - "调整 SaaS 合规边界"
  - "新增滥用治理策略"
downstream:
  - "docs/plans/005-01-自部署浏览器Cookie配置计划.md"
  - "docs/plans/005-02-限流配额与合规负向计划.md"
  - "docs/plans/001-万能视频下载器MVP执行计划.md"
  - "docs/acceptance/001-万能视频下载器MVP测试计划.md"
---

# 自部署 Cookie 与合规治理 PRD

## 1. 背景

用户选择首版允许自部署读取本机浏览器 Cookie，以支持登录后仍公开可访问的内容。该能力必须限制在自部署环境配置中，不应扩展为 SaaS 页面上传 Cookie，也不得用于绕过 DRM、付费墙、会员或私密内容。

## 2. 目标

1. 自部署用户可通过环境变量配置 yt-dlp 从本机浏览器读取 Cookie。
2. 系统明确提示 Cookie 只用于用户本人已授权的公开视频访问。
3. SaaS 形态默认不开放 Cookie 上传、托管、共享或账号池能力。
4. 公网部署必须保留鉴权、限流、配额、并发和文件大小控制。

```gherkin
Given 自部署用户配置了浏览器 Cookie 来源
When Worker 执行下载任务
Then 系统只在本机环境读取浏览器 Cookie
And 不提供网页上传或账号共享能力
And 受限、付费、会员或 DRM 内容仍然失败并提示边界
```

## 3. 非目标

- 不托管用户平台 Cookie。
- 不提供 Cookie 上传表单、账号池或共享登录态。
- 不绕过付费、会员、DRM、验证码、风控或私密权限。
- 不为公开 SaaS 用户提供平台账号代下服务。

## 4. 核心用户故事

| 用户 | 场景 | 验收标准 |
| --- | --- | --- |
| 自部署用户 | 本机浏览器已登录平台 | 可通过环境变量启用浏览器 Cookie 读取 |
| SaaS 管理员 | 控制滥用风险 | 默认不出现 Cookie 上传入口 |
| 合规审核者 | 审查产品边界 | 文档和错误提示明确禁止绕过受保护内容 |

## 5. 治理规则

1. API 必须启用登录鉴权。
2. 解析和创建任务必须有限流。
3. 用户有日任务数、并发数、文件大小、存储额度和保留时间限制。
4. 日志、错误和事件不得泄露 Cookie、token、signature、auth、key、access_token、session。
5. 高风险平台或受限内容失败时不得继续尝试规避。

## 6. 首版验收门禁

- `YTDLP_COOKIES_FROM_BROWSER` 只接受受支持浏览器名称或关闭值。
- 无效 Cookie 配置返回明确错误。
- 文档中明确“自部署可选、本机读取、不上传、不托管、不共享”。
- 合规边界覆盖 DRM、付费墙、会员、私密内容、批量抓取和账号共享。

## 7. 风险与边界

即使是本机 Cookie，也可能触发平台风控或违反平台条款。产品必须把该能力描述为自部署用户自行配置的高级选项，而不是默认卖点。

## 8. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 初始化自部署 Cookie 与合规治理 PRD |
