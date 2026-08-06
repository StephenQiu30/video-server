# Contributing

感谢你愿意改进 `server`。

## 模块边界

- `backend/`：FastAPI、领域服务、Worker、当前态 SQL 与 Python 测试。
- `frontend/`：Ant Design Pro / Umi Max 页面、组件、OpenAPI 客户端与前端测试。
- `docs/`：当前产品和架构事实。
- 根 `Dockerfile` 与三个 `docker-compose*.yml`：唯一部署入口，不建立独立部署目录。

功能交付遵循 `Design → PRD → Plan → Acceptance`，并保持测试、契约、文档和实际运行方式一致。具体目录、依赖、安全、配置和测试规则以 `AGENTS.md` 为准。提交前分别运行后端与前端质量门禁；涉及运行时变更时还需验证三个根 Compose 配置和统一镜像构建。

安全边界和漏洞报告方式见 `SECURITY.md`；任何下载能力变更都必须保留公开、授权、非 DRM 的产品边界。

## 提交规范

每个可独立验证的小任务对应一个提交。提交信息遵循 Conventional Commits，并使用中文描述：

```text
<type>(<scope>): <中文描述>
```

作用域可省略；省略时使用 `<type>: <中文描述>`，不要保留空括号。推荐类型如下：

| 类型 | 用途 |
| --- | --- |
| `feat` | 新增用户可见能力 |
| `fix` | 修复缺陷 |
| `refactor` | 不改变外部行为的代码重构 |
| `docs` | 仅修改文档 |
| `test` | 新增或调整测试 |
| `perf` | 性能优化 |
| `build` | 构建系统或依赖变更 |
| `ci` | 持续集成配置变更 |
| `chore` | 其他维护工作 |
| `style` | 不影响逻辑的格式调整 |
| `revert` | 回退已有提交 |

作用域使用稳定、非空的小写英文模块名，如 `api`、`frontend`、`backend`、`runner`、`worker`、`docs`、`deps`。描述使用简洁的中文动作短语，不加句号：

```text
feat(api): 增加下载任务取消接口
fix(frontend): 修复任务状态轮询泄漏
refactor(worker): 拆分分析任务持久化逻辑
docs: 补充本地开发说明
```

`feat(): 增加功能` 不是合法格式：使用作用域时必须填写括号内容，不需要作用域时应写成 `feat: 增加功能`。

破坏性变更使用 `!` 标记，并在提交正文中提供 `BREAKING CHANGE:` 说明：

```text
feat(api)!: 移除旧下载接口
```

提交前只暂存当前任务文件并完成相关验证；提交后运行 `git status --short`，确保没有本任务遗留的未提交文件。只有在明确要求时才推送远端或创建 PR。
