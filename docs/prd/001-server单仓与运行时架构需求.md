# 001 Server 单仓与运行时架构需求

- 状态：Accepted
- 关联 Design：`docs/design/001-server单仓与运行时架构设计.md`

## 用户结果

开发者只需克隆一个 `server` 仓库，即可开发前端、后端、Worker 并启动完整环境；部署者只需管理一个应用镜像，浏览器只配置一个公开 Origin。

## 功能需求

1. 仓库必须包含 `backend/`、`frontend/`、`docs/` 三个明确模块，Dockerfile 和三种 Compose 配置直接位于根目录。
2. 前后端可独立安装依赖、测试和开发；生产构建必须把前端静态产物放进统一 Server 镜像。
3. API、下载 Worker、媒体 Runner 和 AI Worker必须有独立进程入口，可分别扩缩容和重启。
4. 根目录必须提供统一环境模板、Compose、CI 与操作说明。
5. 页面、API、下载地址签发和分析查询必须通过同一个公开 Origin；前端不保存服务端密钥。

## 非功能需求

- 单仓变更必须同时通过 Python 和 TypeScript 质量门禁。
- 目录改名不得隐式切换 PostgreSQL、RabbitMQ、MinIO 的持久卷。
- 业务模块不得形成反向依赖；Domain 必须可在无基础设施的情况下单测。
- 旧两仓提交历史必须可追溯，但旧实现与旧验收不进入当前运行路径。

## 不在本需求内

本需求不证明下载或 AI 业务正确；两者分别由 002、003 交付链验收。
