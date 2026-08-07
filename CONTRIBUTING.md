# Contributing

感谢你愿意改进 `server`。

## 模块边界

- `backend/`：FastAPI、领域服务、Worker、当前态 SQL 与 Python 测试。
- `frontend/`：Ant Design Pro / Umi Max 页面、组件、OpenAPI 客户端与前端测试。
- `docs/`：当前产品和架构事实。
- 根 `Dockerfile`、`docker-compose.yml` 与 `docker-compose-prod.yml`：唯一运行入口，不建立独立部署目录。基础 Compose 负责完整本地环境，生产 Compose 只覆盖生产差异。

功能交付遵循 `Design → PRD → Plan → Acceptance`，并保持测试、契约、文档和实际运行方式一致。具体目录、依赖、安全、配置和测试规则以 `AGENTS.md` 为准。提交前分别运行后端与前端质量门禁；涉及运行时变更时还需验证本地 Compose、生产 Compose 组合和统一镜像构建。

安全边界和漏洞报告方式见 `SECURITY.md`；任何下载能力变更都必须保留公开、授权、非 DRM 的产品边界。

## 提交规范

每个可独立验证、可安全回滚的小任务对应一个提交。提交信息遵循 Conventional Commits，类型和作用域使用小写英文，冒号后的描述必须使用中文：

```text
<type>(<scope>): <中文描述>
```

作用域可省略；省略时使用 `<type>: <中文描述>`，不要保留空括号。标题最多 72 个字符，使用明确的中文动作短语，末尾不加标点。推荐类型如下：

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

作用域使用稳定、非空的小写英文模块名，如 `api`、`frontend`、`backend`、`runner`、`worker`、`docs`、`deps`。无法准确归属时省略作用域，不要临时发明含糊缩写：

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

BREAKING CHANGE: 客户端需要迁移到新版下载接口
```

正文用于解释修改动机、实现方式和影响，与标题之间保留一个空行；关联任务可在页脚写 `Refs: #123`。不要在标题中堆叠实现细节。

首次克隆后运行以下命令，启用仓库提供的提交模板和本地校验钩子：

```bash
git config commit.template .gitmessage
git config core.hooksPath .githooks
```

本地钩子和 CI 使用同一个校验脚本。也可以在提交前手动检查：

```bash
python scripts/validate_commit_message.py --message "feat(frontend): 优化视频下载页面"
```

提交前只暂存当前任务文件并完成相关验证；提交后运行 `git status --short`，确保没有本任务遗留的未提交文件。只有在明确要求时才推送远端或创建 PR。包括合并和回退在内的所有提交均执行上述中文规范，不设置格式豁免或兼容分支。
