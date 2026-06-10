---
layer: Plan
doc_no: "10"
audience:
  - Dev
  - Ops
feature_area: docker-compose-deployment-health
purpose: "实现 PRD05 中的 Docker Compose 部署路径和健康检查闭环。"
canonical_path: "docs/plans/10-DockerCompose部署与健康检查计划.md"
status: draft
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/05-自部署运行与环境复用.md"
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
outputs:
  - "Docker Compose 部署与健康检查计划"
triggers:
  - "需要完善自部署交付路径"
downstream:
  - "docs/operations/01-个人自部署万能视频下载器运行与部署.md"
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PLAN10 Docker Compose 部署与健康检查

## 1. 背景

对个人自部署用户来说，Docker Compose 是最直接的完整交付方式。

## 2. 目标

1. 提供一键启动完整服务的部署路径。
2. 定义健康检查和启动后验证方式。

## 3. 非目标

- 不做 Kubernetes 或云平台部署方案。

## 4. 核心内容

1. 明确 API、Worker、Redis、Postgres、MinIO 的 Compose 角色。
2. 给出启动、停止和健康检查步骤。
3. 对常见启动失败给出排查路径。

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/05-自部署运行与环境复用.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/operations/01-个人自部署万能视频下载器运行与部署.md`

### 5.3 下游文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

## 6. 验收门禁

- Docker Compose 可启动完整系统。
- 健康检查覆盖 API 和核心依赖。

## 7. 风险与边界

Compose 文件和本机开发配置分叉过大，会让维护成本显著上升。

## 8. 待确认问题

- 是否拆分最小 profile 与完整 profile。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN10 |
