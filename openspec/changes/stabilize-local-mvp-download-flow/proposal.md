# Stabilize Local MVP Download Flow

## Why

M1 已经切换为本地单用户 MVP，但当前闭环仍有三个阻塞点：前端视觉过度定制，下载链接暴露 MinIO 内部地址导致浏览器不可用，任务失败后的补救和事件可见性不足。

## What Changes

- 将前端收回到 Ant Design Pro 原生工作台组件，移除过度设计样式。
- 将下载交付改为后端短期签名代理 URL，避免前端直接打开 MinIO / S3 内部地址。
- 增加任务事件查询和失败/取消/过期任务重试，重试创建新任务并保留旧任务历史。
- 同步 M1 文档和 AGENTS 规则，明确当前阶段为本地单用户、无登录认证。

## Impact

- Affected specs: `video-download-tasks`, `object-storage-delivery`, `project-runtime-foundation`
- Affected code: FastAPI tasks API, storage service, worker failure classification, React/Umi frontend, smoke scripts, docs
