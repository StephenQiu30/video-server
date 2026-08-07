# 001 Server 单仓与运行时架构验收

- 状态：Executed
- 结论：Passed

## 验收项

- [x] 根目录仅一套 Git、治理、文档、环境和 CI。
- [x] `backend/` 与 `frontend/` 模块边界和依赖方向符合 Design。
- [x] 后端 Ruff、format、mypy、pytest 全部通过。
- [x] 前端 lint、format、typecheck、tests、production build 全部通过。
- [x] Compose config 可解析，统一镜像包含 Python runtime 与 frontend dist。
- [x] 数据库只保留 `backend/sql/schema.sql` 当前态定义，不存在迁移目录或兼容升级路径。
- [x] FastAPI 同源提供 `/`、SPA 深链接、静态资源和 `/api/*`，未知 API 不回退到 HTML。
- [x] 本地和生产应用 Compose 不存在独立 frontend/Nginx 服务，统一镜像由 FastAPI 同源提供前端。
- [x] Media Runner 通过 egress proxy 出网，proxy 阻断私网、localhost 和字面量 IP 目的地址。
- [x] builder 与 runtime 的 `/app/backend/.venv` 绝对路径一致，所有 Python 进程入口可从统一镜像启动。
- [x] 本地应用、生产应用和基础设施使用稳定且独立的 Compose 项目名、容器名和作用域卷，不会并行争用同一数据卷。
- [x] 本地应用和基础设施 Compose 读取被 Git 忽略的 `.env`，生产应用 Compose 读取 `.env.prod`；环境变量值不写入非 env 文件。
- [x] 原后端与前端历史可从 Git 提交/标签恢复。

## 验证命令

```bash
cd backend && uv run ruff check . && uv run ruff format --check .
cd backend && uv run mypy --strict app && uv run pytest -q
cd frontend && npm run lint && npm run format:check && npm test && npm run build
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose-env.yml config --quiet
docker compose -f docker-compose-prod.yml config --quiet
docker build --target runtime --tag video-server:architecture .
```

## 执行证据（2026-08-06）

- 后端：Ruff、format、strict mypy 与 `pytest -q` 全部通过。
- 前端：Biome lint、format、TypeScript、Vitest 与 Umi Max production build 全部通过。
- 测试策略：CI 不设置覆盖率数字硬门槛；测试聚焦领域规则、API 契约、安全边界和关键流程，不为覆盖率重复测试实现细节。
- 依赖：`npm audit --audit-level=high` 为 0 vulnerabilities。
- 数据库：仓库中只有 `backend/sql/schema.sql`，由 PostgreSQL 在全新数据卷首次启动时执行；没有 Alembic/migrations 或旧 schema 兼容分支。
- Compose：根目录保留 `docker-compose.yml`、`docker-compose-env.yml`、`docker-compose-prod.yml` 三份独立入口；本地应用、基础设施和生产应用配置均可单独解析，不通过文件叠加启动。
- 配置收敛：镜像、宿主机绑定、容器内部服务名、队列、网络和卷由 Compose 声明；环境变量值只保留在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中。
- 镜像：`docker build --target runtime --tag video-server:architecture .` 返回 0；根目录多阶段 `Dockerfile` 统一构建 frontend dist 与 Python runtime，API、Outbox、下载 Worker、AI Worker 和 Media Runner 复用同一 runtime 镜像。
- 容器入口修复：backend-builder 与 runtime 均使用 `/app/backend`，虚拟环境固定为 `/app/backend/.venv`，Runner 改由 `python -m uvicorn ...` 启动；本地和生产应用 Compose 中 API、Outbox、下载 Worker、AI Worker 与 Media Runner 使用独立栈进入运行/健康状态。
- 应用交付网络：本地 API 固定暴露 `127.0.0.1:8101`，生产 API 暴露 `8101`，真实浏览器能够访问 API，并通过 API 签发的 MinIO URL 取回文件；Media Runner 仍通过 egress proxy 出网。
- 容器 smoke：`/health/ready` 返回 `ok`；`/` 与 `/downloads/example` 返回同一 SPA；未知 `/api/not-found` 返回 JSON 404。
- 历史：原服务端 HEAD 有迁移前标签 `backup/pre-server-monorepo-20260806`；前端历史通过 subtree commit `d8a1d0a` 并入当前分支。

所有预定义条件已满足，结论为 Passed。
