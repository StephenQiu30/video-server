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
3. 对常见启动失败给出排查路径。

## 3. 非目标

- 不做 Kubernetes 或云平台部署方案。

## 4. 核心内容

1. Compose 文件结构：`docker-compose.yml`（基础层，定义 api 和 worker）+ `docker-compose.prod.yml`（覆盖层，添加 postgres、redis、minio 基础设施）。
2. 多阶段 Dockerfile：`python-base`（Python 3.12-slim + ffmpeg）、`api`（安装 API 依赖，uvicorn 监听 8000）、`worker`（安装 Worker 依赖，运行 `python -m worker.main`）。
3. 基础设施版本：`postgres:16-alpine`、`redis:7-alpine`、`minio/minio:latest`。三者均有 healthcheck，应用服务通过 `depends_on` + `condition: service_healthy` 等待就绪。
4. 环境校验：`scripts/validate_prod_env.py` 强制 `.env.production` 中不得含有 `CHANGE_ME` 占位符，且关键 URL 不得指向 localhost。
5. 启动命令：`npm run docker:up`（后台模式）或 `npm run docker:logs`（查看日志），底层调用 `scripts/start.sh docker:up`。
6. 健康检查：API 容器内置 healthcheck（每 10 秒请求 `/health`），基础设施容器各有独立 healthcheck（pg_isready、redis-cli ping、minio curl）。
7. **已知限制**：Worker 服务没有内置健康检查端点，Docker Compose 中无法直接探测 Worker 存活状态，只能依赖进程存在性。
8. 验证：`curl http://localhost:8000/health` 检查存活，`curl http://localhost:8000/ready` 检查全部组件就绪。
9. 停止：`npm run docker:down` 执行 `docker compose down`。

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

Compose 文件和本机开发配置分叉过大，会让维护成本显著上升。当前方案通过统一 `.env.example` 模板和独立 `.env.production` 来缓解，但两者的变量名必须保持同步。

`docker-compose.prod.yml` 中 MinIO 默认凭据使用了占位值（`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY`），部署者必须在 `.env.production` 中覆盖，否则存在安全风险。

## 8. 待确认问题

- 是否拆分最小 profile 与完整 profile（当前为完整 profile，含 MinIO）。
- 是否为 Worker 服务添加健康检查端点以支持 Docker Compose 健康探测。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN10 |
