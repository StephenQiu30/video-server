# Backend

FastAPI API、下载/分析领域逻辑、异步 Worker、当前态数据库 SQL 和 Python 测试位于本模块。

所有 Python 与 `uv` 命令都应从 `backend/` 执行。数据库当前结构定义在 `sql/schema.sql`，由 PostgreSQL 在全新数据卷中初始化；项目不维护迁移或旧 schema 兼容路径。生产镜像由仓库根目录 `Dockerfile` 统一构建。
