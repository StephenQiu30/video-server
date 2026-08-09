# 001 Server 单仓与运行时架构计划

- 状态：Completed

## 任务

1. 以原服务端历史为 canonical，通过 Git subtree 导入完整前端历史。
2. 重命名本地项目为 `server`，清理子仓治理、重复部署与旧业务实现。
3. 建立 `backend/app`、`frontend/src` 和当前 `docs` 骨架；部署文件直接置于根目录。
4. 重写统一多阶段 Dockerfile、Compose、环境模板和 CI。
5. FastAPI 同源挂载 Next.js 静态导出；保留开发代理。
6. 增加结构、静态托管、前后端构建与 Compose 配置测试。
7. 记录 Git/卷/镜像回滚方式并执行 Acceptance。

## 退出条件

001 Acceptance 已于 2026-08-06 判定 Passed，002 下载业务实现可以进入主线。

## 完成证据（2026-08-06）

- 后端 `pytest -q` 与前端 Vitest 全量门禁均通过；文档不固化会随实现变化的用例数量。
- CI 不设置覆盖率硬门槛，保留 Ruff、format、strict mypy、核心测试和生产构建门禁。
- 数据库只使用 `backend/sql/schema.sql` 初始化全新 PostgreSQL 数据卷，不维护 migrations 或兼容升级路径。
- 根目录两份 Compose 按职责分层：`docker-compose.yml` 负责完整本地拓扑和本地环境差异，`-prod` 负责生产环境差异。
- 本地独立使用 `docker-compose.yml`，生产使用 `docker-compose.yml` 叠加 `docker-compose-prod.yml`；环境变量值不写入非 env 文件。
- 根多阶段 Dockerfile 产出包含 frontend dist 的统一 runtime 镜像，各代码进程复用该镜像。
- backend-builder 与 runtime 的绝对工作目录统一为 `/app/backend`，复制后的 `.venv` 路径不变；Python 服务使用 `python -m ...` 入口。API 固定通过 `127.0.0.1:8101` 提供应用入口，签名文件地址由 API 生成。
