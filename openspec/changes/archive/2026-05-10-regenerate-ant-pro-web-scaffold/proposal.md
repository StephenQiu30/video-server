# Regenerate Ant Pro Web Scaffold

## Why

当前前端虽然运行在 Umi Max / Ant Design ProLayout 下，但页面内容仍包含自定义页面外壳、宽度控制和下载器专用布局样式。M1 需要回到 Ant Design Pro 脚手架和 ProComponents 原生页面结构，避免继续手写页面尺寸和过度设计。

## What Changes

- 基于官方 `create-umi` 的 Ant Design Pro 模板结构重整 `apps/web` 页面组织。
- 前端页面统一使用 ProLayout、PageContainer、ProCard、ProForm、ProList、ProTable 等组件承载布局和内容。
- 移除自定义页面尺寸控制，不再用 `.page-shell`、`.download-workspace` 作为主布局容器。
- 保留现有下载业务能力：链接解析、清晰度选择、创建任务、SSE 进度、下载、重试、取消和任务历史。
- 不修改后端 API、Worker、下载内核、对象存储、数据库或生产 SaaS 能力。

## Impact

- Affected specs: `web-download-workspace`
- Affected code: `apps/web` 前端脚手架结构、页面、运行时布局、全局样式、前端验收文档
