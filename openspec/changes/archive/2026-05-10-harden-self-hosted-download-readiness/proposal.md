# Harden Self Hosted Download Readiness

## Why

当前项目已经适合个人本机或自部署使用，但下载稳定性、任务清理、运行诊断和自部署 smoke 还不够完整。公网 SaaS 所需的登录、管理员、配额、限流和 TLS 门禁仍归 `production-saas-readiness` 管理，本变更只补齐个人自部署下载链路的稳定性。

## What Changes

- 强化 Worker 下载重试、取消检测、进度事件和失败原因归类。
- 增强 `/ready` 诊断，补充队列和下载工作目录检查。
- 新增过期文件清理脚本和个人自部署 smoke 聚合脚本。
- 更新中文文档，明确本变更不等于公网 SaaS 放行。

## Impact

- Affected specs: `video-download-tasks`, `project-runtime-foundation`
- Affected code: Worker 下载任务、健康检查、前端轻量状态提示、脚本、文档和测试
