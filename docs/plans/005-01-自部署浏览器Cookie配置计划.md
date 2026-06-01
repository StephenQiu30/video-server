---
layer: Plan
doc_no: "005-01"
audience:
  - Dev
  - QA
  - Ops
feature_area: self-hosted-browser-cookie
purpose: "将 PRD 005 拆解为自部署浏览器 Cookie 配置执行计划。"
canonical_path: "docs/plans/005-01-自部署浏览器Cookie配置计划.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/005-自部署Cookie与合规治理.md"
outputs:
  - "自部署 Cookie 配置实现任务"
triggers:
  - "调整 YTDLP_COOKIES_FROM_BROWSER 或下载登录态配置"
downstream:
  - "docs/acceptance/001-万能视频下载器MVP测试计划.md"
---

# 自部署浏览器 Cookie 配置计划

## 1. 背景

自部署用户可以选择让 yt-dlp 从本机浏览器读取 Cookie，但产品不能提供 SaaS 上传、托管或共享登录态。

## 2. 目标

- 支持 chrome、chromium、edge、firefox、safari。
- 支持 none、false、off 关闭配置。
- 无效浏览器名返回明确错误。

## 3. TDD 步骤

1. `test:` 在 `apps/api/tests/test_worker_reliability_modules.py` 增加 Cookie 配置校验断言。
2. 运行红灯命令：

```bash
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_worker_reliability_modules.py -q
```

3. `impl:` 调整 `apps/worker/worker/download_runner.py` 的 Cookie 选项处理。
4. 运行绿灯命令并确认错误文案不鼓励绕过。

## 4. 验收门禁

- 支持浏览器名会传入 yt-dlp `cookiesfrombrowser`。
- 关闭值不会设置 Cookie 选项。
- 无效值抛出业务错误。

## 5. Linear 子任务标题

`PRD005-01 自部署浏览器Cookie配置`

## 6. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 初始化计划 |
