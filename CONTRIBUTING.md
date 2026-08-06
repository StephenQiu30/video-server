# Contributing

感谢你愿意改进 `server`。

## 模块边界

- `backend/`：FastAPI、领域服务、Worker、当前态 SQL 与 Python 测试。
- `frontend/`：Ant Design Pro / Umi Max 页面、组件、OpenAPI 客户端与前端测试。
- `docs/`：当前产品和架构事实。
- 根 `Dockerfile` 与三个 `docker-compose*.yml`：唯一部署入口，不建立独立部署目录。

功能交付遵循 `Design → PRD → Plan → Acceptance`，并保持测试、契约、文档和实际运行方式一致。具体目录、依赖、安全、配置和测试规则以 `AGENTS.md` 为准。提交前分别运行后端与前端质量门禁；涉及运行时变更时还需验证三个根 Compose 配置和统一镜像构建。

安全边界和漏洞报告方式见 `SECURITY.md`；任何下载能力变更都必须保留公开、授权、非 DRM 的产品边界。
