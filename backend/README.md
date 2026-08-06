# Backend

FastAPI API、下载/分析领域逻辑、异步 Worker、当前态数据库 SQL 和 Python 测试位于本模块。

所有 Python 与 `uv` 命令都应从 `backend/` 执行。数据库当前结构定义在 `sql/schema.sql`，由 PostgreSQL 在全新数据卷中初始化；项目不维护迁移或旧 schema 兼容路径。生产镜像由仓库根目录 `Dockerfile` 统一构建。

文本分析统一通过 LangChain 的结构化输出接口运行，服务端以 `ANALYSIS_PROVIDER=ollama|deepseek` 选择本地 Ollama 或 DeepSeek。Ollama 默认模型为 `deepseek-r1:8b`，DeepSeek 默认模型为 `deepseek-v4-flash`。音频转录是独立 ASR 端口，不与文本模型配置混用。
