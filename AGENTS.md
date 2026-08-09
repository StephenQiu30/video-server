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
│   │   ├── web/                   Next.js 静态导出、404 与旧路由转发
│   │   ├── composition.py         运行时依赖装配
│   │   └── main.py                FastAPI 入口
│   ├── config/                    Egress、MinIO 等运行配置
│   ├── sql/schema.sql             PostgreSQL 当前态结构
│   └── tests/                     architecture/contract/integration/unit 测试
├── frontend/                      Next.js App Router 前端
│   ├── src/app/                   页面、布局与全局 Tailwind 主题
│   ├── src/
│   │   ├── components/            业务组件与 shadcn/ui 源码
│   │   ├── hooks/                 可复用状态和流程 Hooks
│   │   ├── lib/                   Axios 请求基础设施与通用工具
│   │   ├── services/              业务请求入口与 OpenAPI 生成代码
│   │   ├── types/                 前端业务类型
│   │   ├── utils/                 无 UI 的通用函数
│   │   └── requestErrorConfig.ts  统一请求错误处理
│   └── tests/                     Vitest 测试
├── docs/                          当前设计、需求、计划、验收与运维文档
├── Dockerfile                     前后端统一生产镜像
├── docker-compose.yml             本地完整服务拓扑（.env、宿主机端口）
└── docker-compose-prod.yml        生产环境覆盖（.env.prod、镜像与端口）
```

仓库只保留 `backend/`、`frontend/`、`docs/` 三个业务模块和根治理文件，不新增 `deploy/`、重复子仓库或平行应用目录。生产环境不运行独立前端容器，静态资源由根镜像构建并通过 FastAPI 同源提供。

## 文件放置规则

- FastAPI 路由只负责协议转换、依赖注入和调用应用用例；业务规则不得写在 `api/`。
- 请求与响应模型放在 `api/schemas/`，不得直接暴露 ORM 模型或基础设施对象。
- 用例编排和外部能力接口放在 `application/`；纯业务规则放在 `domain/`；具体 SDK、数据库、消息和存储实现放在 `infrastructure/`。
- 进程入口放在 `workers/` 或 `runner/`，不要把下载、转码、ASR 或 LLM 长任务放进 HTTP 请求进程。
- 前端不使用 `features/` 目录。App Router 页面放在 `src/app/`，跨页面业务组件放在 `src/components/`，shadcn/ui 源码放在 `src/components/ui/`。
- 前端请求统一从 `services/` 暴露，状态流程优先放在 `hooks/`；不要在页面中散落原始请求、轮询或错误映射逻辑。
- `frontend/src/services/video/` 由 `@umijs/openapi` 的 `npm run openapi` 命令根据 FastAPI Swagger/OpenAPI 契约生成，禁止手工修改。生成代码统一导入 `frontend/src/lib/request.ts` 的 Axios 请求封装；接口变化时先更新并启动 API，再重新生成服务文件。
- 后端公开操作必须声明稳定且唯一的 `operationId` 和 tag，供 OpenAPI 类型生成和契约测试使用。创建出可查询资源的接口返回 `201 Created` 和 `Location`；异步执行状态放在响应模型中，不用 `202` 损失返回类型。
- 路由、布局和元数据遵循 Next.js App Router 官方约定；交互组件使用 shadcn/ui 与 Radix UI，样式使用 Tailwind CSS 主题 token，不得重新引入 Umi、Ant Design、Vite 入口或平行路由器。
- 测试目录应与被测职责对应；通用测试数据和 Fake 可以复用，但不得为了覆盖率复制实现细节。

## 前端设计系统规范（强制）

本项目唯一视觉方向是用户确认的“方案 3”：Vercel Home 式无边框界面。详细设计决策见 [009 前端视觉系统设计](docs/design/009-Next前端与蓝白视觉系统设计.md)，视觉回归证据见 [设计 QA](design-qa.md)。本节是所有前端变更必须满足的仓库级门禁；`frontend/src/app/globals.css` 是 token 和布局公式的可执行事实来源。三者不一致时视为缺陷，必须在同一变更中同步，不得另建平行规范。

### 视觉、token 与网格

- 画面以内容、排版和留白组织层级：浅色主题使用 `#FAFAFA` 画布、`#0A0A0A` 前景和 `#111111` 主操作；深色主题使用 `#0A0A0A` 画布、`#F5F5F5` 前景。控件表面、弱化文字、边界、成功、警告和错误只能消费 `background`、`foreground`、`surface`、`muted`、`primary`、`border`、`success`、`warning`、`destructive` 等语义 token，不在业务组件中散落十六进制色值或近似色。
- 基础圆角为 `6px`，只通过 `--radius` 派生。默认不使用阴影；层级优先依靠明度、间距和排版，覆盖层仅保留识别层级所必需的表面与遮罩。
- 所有路由复用两级隐形网格：72px Header 使用 `.page-shell = min(calc(100% - 80px), 1456px)`，常规 main/footer 使用 `.content-shell = min(calc(100% - 160px), 1376px)`。认证页的无外框双栏 main 是唯一例外，可使用 `.page-shell`，但表单必须在内部收窄到 440px；不足 `lg` 时隐藏介绍栏。641–1023px 时内容区两侧各 32px；不超过 640px 时两级网格两侧均为 16px。网格只负责对齐，不得被渲染成可见应用外壳。
- 字体统一为自托管 Geist Sans/Mono，中文按 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei`、系统无衬线顺序回退。首页编辑式标题复用 `.editorial-title`（`clamp(3.2rem, 5.4vw, 4.25rem)`、字重 500、行高 0.96、负字距）；页面主标题上方的编号眉题只在真实流程步骤存在时使用 `.eyebrow` 和 Geist Mono，普通区段可克制复用同一小标题样式，但不得编号或重复 H1。内页保持短标题与清晰层级，不增加装饰标签或营销式副标题。

### 控件、组件与交互

- 页面根、标题区、筛选区、列表区和表单区禁止可见 Card 外壳、装饰性 border/ring、重阴影和大面积圆角容器。Input、Select、Button 等默认使用无边框实心中性表面；内容分组只使用必要的 1px 发丝 Separator。错误边界、键盘焦点轮廓和 Radix 覆盖层边界属于功能反馈，不得以“无边框”为由移除。
- 交互原语优先组合 `frontend/src/components/ui/` 中 shadcn/ui `radix-nova` 源码与 Radix UI。Dialog、AlertDialog、Sheet、Select、Dropdown Menu、Tabs、RadioGroup、Progress、Tooltip 等必须保留语义、焦点圈定、Escape 行为和触发器焦点恢复；不得用可点击 `div`、自制浮层或第二套基础组件绕过这些能力。
- 图标只使用 `@phosphor-icons/react` 的同一家族，并提供可访问名称；禁止用 emoji、文本符号、CSS 图形、临时手绘 SVG 或混用图标库代替业务图标。
- 所有已认证的非首页页面与多步骤流程必须提供明确、可键盘操作的返回路径。返回上一步优先遵循由应用记录的站内浏览历史，并为无可用历史的直接访问提供稳定站内 fallback；登录与注册不渲染通用历史返回，改用彼此之间的明确交叉链接和校验后的 `redirect`，避免过期受保护页面参与回退并形成认证循环。不得让用户只能依赖浏览器工具栏，也不得用硬编码跳转破坏正常返回链路。
- 首页格式选择必须用 Radix RadioGroup 渲染 API 返回的真实 `MediaFormat`。界面不得虚构后端没有的画质预设、字幕、容器、音频模式、文件大小、播放能力或任务状态。

### 响应式、状态与可访问性

- 390×844 是强制移动验收视口，桌面同时覆盖 1280px 与方案稿桌面尺寸。页面不得产生横向滚动；固定尺寸必须受 `max-width: 100%` 约束。移动端重排信息而非缩放桌面：导航进入 Sheet，输入/主操作纵向满宽，媒体与格式单列，表格转换为可读 Item，Dialog/Sheet 内容可滚动。
- 每个异步流程都必须设计并验证初始、加载、成功、空、校验失败、请求失败、禁用和重试状态；状态不能只靠颜色表达，也不得用空白区域冒充失败或无数据。轮询状态通过节流的 `aria-live` 播报，避免每次刷新重复朗读。
- 目标为 WCAG 2.2 AA：语义化结构、唯一 `h1`、顺序标题、真实 label/button/table、正文至少 4.5:1 对比度、可见 `2px` 焦点环与 `2px` 偏移、至少 44×44px 触控目标、完整键盘路径、准确图片替代文本，并遵循 `prefers-reduced-motion`。Tooltip 不能承载唯一必要信息。
- 生产界面优先使用真实媒体封面；失败时显示准确的不可用状态。视觉回归专用山景资产固定为 `frontend/public/images/media-preview-mountain.webp`，新增位图必须按显示尺寸裁切并优先压缩为 WebP/AVIF，禁止提交无用途原图、外链热链、伪造业务数据或仅用于装饰的大图。

### 禁止事项与变更门禁

- 禁止恢复侧栏后台壳、卡片堆叠、三步向导、高密度工具栏、渐变炫光、玻璃拟态、重投影或蓝色企业后台视觉；禁止重新引入 Ant Design、Ant Design Pro、Umi、Less、CSS-in-JS 或平行主题系统。
- 修改颜色、字体、圆角、网格、断点或基础控件时，必须同步更新 `globals.css`、[009 设计文档](docs/design/009-Next前端与蓝白视觉系统设计.md) 和必要测试；修改导航模式或核心页面信息层级时，必须同步更新 009 设计文档与必要测试。视觉基准变化还必须重做 [design-qa.md](design-qa.md) 的桌面/390px 同状态比较。
- 交付前至少运行前端 `npm run lint`、`npm run format:check`、`npm test`、`npm run build`，并实际检查键盘返回路径、明暗主题、加载/空/错误状态、Radix 覆盖层和页面级横向溢出。视觉 QA 只有在没有剩余 P0/P1/P2 差异且 `design-qa.md` 写明 `final result: passed` 时才算通过；QA 截图不能替代功能和无障碍验证。

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
- Compose 必须保持职责清晰：`docker-compose.yml` 是可独立启动的本地完整配置，定义服务拓扑、依赖关系、健康检查、卷、内部端口、本地 `.env` 和宿主机端口；`docker-compose-prod.yml` 只覆盖生产 `.env.prod`、生产镜像和对外端口。生产命令必须显式传入 `--env-file .env.prod`，生产覆盖必须使用 `${VAR:?set VAR in .env.prod}` 在 Compose 解析阶段校验关键配置。本地只使用 `docker-compose.yml`，生产使用 `docker-compose.yml` 叠加 `docker-compose-prod.yml`，不得再维护独立的环境覆盖文件。宿主机端口通过 env 文件插值并提供安全默认值，生产覆盖移除本地基础设施端口；环境变量的具体值只能写在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中，非 env 文件不得硬编码密钥、密码、连接地址或 Provider Key。所有服务必须显式设置稳定的 `container_name`；公开主服务使用 `video-server`，基础服务使用 `postgres`、`rabbitmq`、`minio` 等简单名称，避免出现 `xxx-1` 这类副本后缀。本地和生产统一使用 Compose 项目名 `video-server` 及其作用域卷，因此同一主机不要同时启动两套环境。启动前按需复制 `.env.example` 为 `.env`，生产环境复制 `.env.prod.example` 为 `.env.prod` 并替换占位值。不要提交 `.env`、制品、缓存、日志、临时目录、虚拟环境或 `node_modules/`。

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

- 涉及接口契约时验证 OpenAPI 生成结果和前后端契约测试；涉及运行时、依赖或容器时分别验证本地配置（`docker-compose.yml`）和生产组合（`docker-compose.yml` + `docker-compose-prod.yml`）可以解析，按需验证镜像构建和关键健康接口。
- 不得隐瞒失败的检查。无法在当前平台完成的验证应在交付说明中写明原因、已执行范围和剩余风险。

## 文档规范

- 根 `README.md` 说明仓库入口和运行方式；`backend/README.md`、`frontend/README.md` 说明模块用法；详细事实放在 `docs/`，不要在多个文件复制大段内容。
- 功能资料按 `Design → PRD → Plan → Acceptance` 维护。架构、目录、命令、配置或验收状态变化时，同步更新对应文档。
- 文档只描述当前真实实现；历史方案通过 Git 追溯，不保留已废弃内容作为“兼容说明”。

## Git 与任务交付

- 开始任务和提交前都执行 `git status --short`，识别并保留用户已有改动；不得覆盖、删除或顺带提交与当前任务无关的文件。
- 一个“小任务”应是可独立说明、可独立验证、可安全回滚的一组改动。完成并通过相关检查后立即提交，不把多个无关任务积累到同一提交。
- 提交信息遵循 Conventional Commits，格式为 `<type>(<scope>): <中文描述>`；不需要作用域时使用 `<type>: <中文描述>`，禁止使用空作用域 `feat(): ...`。标题最多 72 个字符，中文描述末尾不加标点，并通过 `scripts/validate_commit_message.py` 校验。
- `type` 使用小写英文：新功能 `feat`、缺陷修复 `fix`、重构 `refactor`、文档 `docs`、测试 `test`、性能 `perf`、构建 `build`、持续集成 `ci`、维护 `chore`、纯格式 `style`、回退 `revert`。
- `scope` 使用稳定且非空的小写英文模块名，例如 `api`、`frontend`、`backend`、`runner`、`worker`、`docs` 或 `deps`；无法准确归属时省略作用域，不得临时发明含糊缩写。
- 冒号后使用简洁、明确的中文动作描述，不加句号，例如 `feat(api): 增加下载任务取消接口`、`fix(frontend): 修复任务状态轮询泄漏`、`docs: 补充本地开发说明`。
- 破坏性变更在类型或作用域后添加 `!`，例如 `feat(api)!: 移除旧下载接口`，并在提交正文中使用 `BREAKING CHANGE: <中文说明>` 描述迁移影响。
- 提交前检查暂存区，只暂存当前任务文件；禁止提交 Secret、缓存、构建产物、日志、临时文件或无意义格式化改动。
- 提交完成后再次执行 `git status --short`，正常情况下工作区必须为空。若任务开始时已有用户未提交改动，应原样保留并在交付时明确说明，不能为了“干净”而擅自清理。
- 只有用户明确要求时才推送远端、创建分支或发起 PR。不得擅自改写已有提交、强制推送或使用破坏性 Git 操作。
- 最终交付说明使用中文，至少包含修改摘要、验证结果、提交哈希和工作区状态；存在未完成项或已知风险时必须明确列出。
