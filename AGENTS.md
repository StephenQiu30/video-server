# Server 项目协作规范

本文件适用于整个仓库，是代码代理和贡献者修改本项目时必须遵循的约定。实现、测试、文档和提交都应反映仓库当前状态，不保留无实际用途的旧结构或兼容层。

## 仓库结构

```text
server/
├── backend/                       Python 3.12 / FastAPI 后端
│   ├── app/
│   │   ├── api/                   HTTP 装配、公共依赖、错误与健康检查
│   │   │   ├── routes/            `/api/*` 接口路由
│   │   │   └── schemas/           请求与响应模型
│   │   ├── application/           用例编排、应用模型与外部能力端口
│   │   ├── domain/                不依赖框架的领域实体、规则与错误
│   │   ├── infrastructure/        数据库、消息、存储、AI 与媒体适配器
│   │   ├── runner/                隔离执行媒体命令的进程
│   │   ├── workers/               Outbox、下载与分析 Worker
│   │   ├── web/                   前端静态资源与 SPA 回退
│   │   ├── composition.py         运行时依赖装配
│   │   └── main.py                FastAPI 入口
│   ├── config/                    Egress、MinIO 等运行配置
│   ├── sql/schema.sql             PostgreSQL 当前态结构
│   └── tests/                     architecture/contract/integration/unit 测试
├── frontend/                      Ant Design Pro / Umi Max 前端
│   ├── config/                    Umi 配置、路由、代理与 ProLayout 设置
│   ├── src/
│   │   ├── components/            跨页面复用组件
│   │   ├── hooks/                 可复用状态和流程 Hooks
│   │   ├── pages/                 路由页面及页面私有组件
│   │   ├── services/              业务请求入口与 OpenAPI 生成客户端
│   │   ├── types/                 前端业务类型
│   │   ├── utils/                 无 UI 的通用函数
│   │   ├── app.tsx                Umi 运行时布局与请求配置
│   │   └── requestErrorConfig.ts  统一请求错误处理
│   └── tests/                     Vitest 测试
├── docs/                          当前设计、需求、计划、验收与运维文档
├── Dockerfile                     前后端统一生产镜像
├── docker-compose.yml             默认完整环境
└── docker-compose-env.yml         本地基础设施环境
```

仓库只保留 `backend/`、`frontend/`、`docs/` 三个业务模块和根治理文件，不新增 `deploy/`、重复子仓库或平行应用目录。生产环境不运行独立前端容器，静态资源由根镜像构建并通过 FastAPI 同源提供。

## 文件放置规则

- FastAPI 路由只负责协议转换、依赖注入和调用应用用例；业务规则不得写在 `api/`。
- 请求与响应模型放在 `api/schemas/`，不得直接暴露 ORM 模型或基础设施对象。
- 用例编排和外部能力接口放在 `application/`；纯业务规则放在 `domain/`；具体 SDK、数据库、消息和存储实现放在 `infrastructure/`。
- 进程入口放在 `workers/` 或 `runner/`，不要把下载、转码、ASR 或 LLM 长任务放进 HTTP 请求进程。
- 前端不使用 `features/` 目录。路由页面放在 `pages/`，跨页面复用组件放在 `components/`，页面私有组件放在该页面的 `components/` 子目录。
- 前端请求统一从 `services/` 暴露，状态流程优先放在 `hooks/`；不要在页面中散落原始请求、轮询或错误映射逻辑。
- `frontend/src/services/video/` 由 `@umijs/max-plugin-openapi` 的 `max openapi` 命令生成，禁止手工修改或另写生成器。OpenAPI 配置统一放在 `frontend/config/config.ts`；接口变化时先更新 FastAPI 契约并启动 API，再运行 `npm run openapi`。
- 后端公开操作必须声明稳定且唯一的 `operationId` 和 tag，供 Umi 生成函数名与文件分组。创建出可查询资源的接口返回 `201 Created` 和 `Location`；异步执行状态放在响应模型中，不用 `202` 损失生成客户端的返回类型。
- 路由、菜单和布局遵循 Ant Design Pro / Umi Max 官方约定，分别由 `config/routes.ts`、`config/defaultSettings.ts` 和 `src/app.tsx` 管理；不得重新引入 Vite 入口、自定义基础布局或平行路由器。
- 测试目录应与被测职责对应；通用测试数据和 Fake 可以复用，但不得为了覆盖率复制实现细节。

## 架构与数据边界

- 后端依赖方向为 `api/workers → application → domain`。`domain` 不得导入 FastAPI、SQLAlchemy、RabbitMQ、MinIO、yt-dlp、FFmpeg 或模型 SDK。
- API、下载 Worker、媒体 Runner、AI Worker 是独立进程。PostgreSQL 是状态事实来源；跨 PostgreSQL/RabbitMQ 使用 transactional outbox，消费者必须支持幂等和 lease/heartbeat。
- PostgreSQL 只通过 `backend/sql/schema.sql` 初始化全新数据库。项目不维护迁移目录、历史 schema 或旧版本兼容逻辑；结构变化时同步更新当前态 SQL、ORM 和测试，并使用新数据卷验证。
- OpenAPI 是前后端接口契约的唯一来源，通过 `/openapi.json` 提供，并由 `/docs` 展示 Swagger UI；不维护平行 DTO、手写生成类型或旧 API 适配层。
- 只实现当前需求，不添加旧目录、旧 API、旧 Provider 或旧数据库的兼容分支。单个源码文件原则上不超过 200 行，超过时按职责拆分。

## 安全与运行约束

- 仅处理用户有权下载和分析的公开、非 DRM HTTP(S) 内容；禁止 Cookie 上传、DRM 绕过、私网 URL、任意 yt-dlp 参数和 shell 输入。
- 媒体流量只能由无业务凭据的 Runner 发起并经过阻断私网的 egress proxy；入口 URL 校验不能替代网络隔离。
- Worker 开工前重新解析语义下载计划；Provider format id 不能作为唯一恢复依据。
- AI 任务独立于下载任务；AI 失败不得改变下载成功状态。模型输出必须通过 schema 和 transcript evidence 校验，普通日志不得记录完整转录或原始模型响应。
- Secret 只来自类型化配置和环境变量，不得进入前端、API 响应、异常、快照、测试夹具或普通日志。外部操作必须设置大小、时长、并发和超时上限，取消时终止整个子进程组。
- Compose 启动方式保持直接清晰：`docker-compose.yml` 启动完整系统，`docker-compose-env.yml` 只启动本地基础设施；不要新增没有明确运行目标的生产覆盖、部署目录或多层启动模板。`.env` 仅用于覆盖本地默认密码、对象存储公开地址或 AI Provider 凭据。不要提交 `.env`、制品、缓存、日志、临时目录、虚拟环境或 `node_modules/`。

## 实现与验证

- 修改前先阅读相邻代码、对应 README 和测试，优先复用现有模型、端口、组件与工具函数。
- 删除失效文件、引用、依赖和文档，不保留“以后可能使用”的空目录、转发层或重复实现。
- 根据改动范围执行最小充分验证；修复缺陷时补充能稳定复现问题的测试。
- 后端命令从 `backend/` 执行：

```bash
uv sync --frozen --dev
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest
```

- 前端命令从 `frontend/` 执行：

```bash
npm ci
npm run lint
npm run format:check
npm test
npm run build
```

- 涉及接口契约时验证 OpenAPI 生成结果和前后端契约测试；涉及运行时、依赖或容器时验证两份 Compose 配置、统一镜像构建和关键健康接口。
- 不得隐瞒失败的检查。无法在当前平台完成的验证应在交付说明中写明原因、已执行范围和剩余风险。

## 文档规范

- 根 `README.md` 说明仓库入口和运行方式；`backend/README.md`、`frontend/README.md` 说明模块用法；详细事实放在 `docs/`，不要在多个文件复制大段内容。
- 功能资料按 `Design → PRD → Plan → Acceptance` 维护。架构、目录、命令、配置或验收状态变化时，同步更新对应文档。
- 文档只描述当前真实实现；历史方案通过 Git 追溯，不保留已废弃内容作为“兼容说明”。

## Git 与任务交付

- 开始任务和提交前都执行 `git status --short`，识别并保留用户已有改动；不得覆盖、删除或顺带提交与当前任务无关的文件。
- 一个“小任务”应是可独立说明、可独立验证、可安全回滚的一组改动。完成并通过相关检查后立即提交，不把多个无关任务积累到同一提交。
- 提交信息遵循 Conventional Commits，格式为 `<type>(<scope>): <中文描述>`；不需要作用域时使用 `<type>: <中文描述>`，禁止使用空作用域 `feat(): ...`。
- `type` 使用小写英文：新功能 `feat`、缺陷修复 `fix`、重构 `refactor`、文档 `docs`、测试 `test`、性能 `perf`、构建 `build`、持续集成 `ci`、维护 `chore`、纯格式 `style`、回退 `revert`。
- `scope` 使用稳定且非空的小写英文模块名，例如 `api`、`frontend`、`backend`、`runner`、`worker`、`docs` 或 `deps`；无法准确归属时省略作用域，不得临时发明含糊缩写。
- 冒号后使用简洁、明确的中文动作描述，不加句号，例如 `feat(api): 增加下载任务取消接口`、`fix(frontend): 修复任务状态轮询泄漏`、`docs: 补充本地开发说明`。
- 破坏性变更在类型或作用域后添加 `!`，例如 `feat(api)!: 移除旧下载接口`，并在提交正文中使用 `BREAKING CHANGE: <中文说明>` 描述迁移影响。
- 提交前检查暂存区，只暂存当前任务文件；禁止提交 Secret、缓存、构建产物、日志、临时文件或无意义格式化改动。
- 提交完成后再次执行 `git status --short`，正常情况下工作区必须为空。若任务开始时已有用户未提交改动，应原样保留并在交付时明确说明，不能为了“干净”而擅自清理。
- 只有用户明确要求时才推送远端、创建分支或发起 PR。不得擅自改写已有提交、强制推送或使用破坏性 Git 操作。
- 最终交付说明使用中文，至少包含修改摘要、验证结果、提交哈希和工作区状态；存在未完成项或已知风险时必须明确列出。
