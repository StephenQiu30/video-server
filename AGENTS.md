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
│   │   ├── composition.py         运行时依赖装配
│   │   └── main.py                FastAPI 入口
│   ├── egress/                    Squid 出口代理策略
│   ├── supply-chain/              后端 SBOM 与第三方声明
│   ├── sql/schema.sql             PostgreSQL 当前态结构
│   └── tests/                     architecture/contract/integration/unit 测试
├── frontend/                      Next.js App Router 前端
│   ├── src/app/                   页面、布局与全局 Tailwind 主题
│   ├── src/
│   │   ├── components/            按 feature 归类的业务组件与 shadcn/ui 源码
│   │   ├── hooks/                 可复用状态和流程 Hooks
│   │   ├── lib/                   Axios、请求错误与通用基础设施
│   │   ├── services/              业务请求入口与 OpenAPI 生成代码
│   │   ├── types/                 前端业务类型
│   │   └── utils/                 无 UI 的通用函数
│   └── tests/                     Vitest 测试
├── docs/                          当前设计、需求、计划、验收与运维文档
├── Dockerfile                     前后端统一生产镜像
├── docker-compose-env.yml         本项目基础环境拓扑
├── docker-compose.yml             本机业务容器拓扑
└── docker-compose-prod.yml        生产业务容器拓扑
```

仓库只保留 `backend/`、`frontend/`、`docs/` 三个业务模块和根治理文件，不新增 `deploy/`、重复子仓库或平行应用目录。生产环境保持前后端分离：Next.js standalone 前端独立监听 `8101`，FastAPI API 独立监听 `8111`。统一镜像按服务启动不同进程；FastAPI 不托管页面。浏览器使用同源相对 API 路径，由 Next.js 或部署入口转发到 API，WebSocket Upgrade 由部署入口直达 FastAPI。

## 文件放置规则

- FastAPI 路由只负责协议转换、依赖注入和调用应用用例；业务规则不得写在 `api/`。
- 请求与响应模型放在 `api/schemas/`，不得直接暴露 ORM 模型或基础设施对象。
- 用例编排和外部能力接口放在 `application/`；纯业务规则放在 `domain/`；具体 SDK、数据库、消息和存储实现放在 `infrastructure/`。
- 进程入口放在 `workers/` 或 `runner/`，不要把下载、转码或 AI 长任务放进 HTTP 请求进程。
- 前端不使用独立的 `src/features/` 目录。App Router 页面放在 `src/app/`，业务组件按 feature 放在 `src/components/{account,admin,analysis,auth,downloads,intake,layout,providers,screenplay}/`，shadcn/ui 源码放在 `src/components/ui/`。
- 前端请求统一从 `services/` 暴露，状态流程优先放在 `hooks/`；不要在页面中散落原始请求、轮询或错误映射逻辑。
- `frontend/src/services/video/` 保留已提交的 OpenAPI 客户端，禁止在页面中绕过稳定入口；生成代码统一导入 `frontend/src/lib/request.ts` 的 Axios 请求封装，接口变化时同步审查契约和客户端。
- 后端公开操作必须声明稳定且唯一的 `operationId` 和 tag，供已提交的 OpenAPI 客户端和契约测试使用。创建出可查询资源的接口返回 `201 Created` 和 `Location`；异步执行状态放在响应模型中，不用 `202` 损失返回类型。
- 路由、布局和元数据遵循 Next.js App Router 官方约定；交互组件使用 shadcn/ui 与 Radix UI，样式使用 Tailwind CSS 主题 token，不得重新引入 Umi、Ant Design、Vite 入口或平行路由器。
- 测试目录应与被测职责对应；通用测试数据和 Fake 可以复用，但不得为了覆盖率复制实现细节。

## 前端设计系统规范（强制）

本项目唯一视觉方向是用户确认的“方案 3”：Vercel Home 式无边框界面。Vercel/Geist 判断基准与产品适配规则见根目录 [design.md](design.md)，详细设计决策见 [前端视觉系统设计](docs/design/frontend-visual-system.md)，视觉回归证据见 [设计 QA](design-qa.md)。本节是所有前端变更必须满足的仓库级门禁；`frontend/src/app/globals.css` 是 token 和布局公式的可执行事实来源。四者不一致时视为缺陷，必须在同一变更中同步，不得另建平行规范。

### 视觉、token 与网格

- 画面以内容、排版和留白组织层级：浅色主题使用 `#FAFAFA` 画布、`#0A0A0A` 前景和 `#111111` 主操作；深色主题使用 `#0A0A0A` 画布、`#F5F5F5` 前景。控件表面、弱化文字、边界、成功、警告和错误只能消费 `background`、`foreground`、`surface`、`muted`、`primary`、`border`、`success`、`warning`、`destructive` 等语义 token，不在业务组件中散落十六进制色值或近似色。
- 基础圆角为 `6px`，只通过 `--radius` 派生。默认不使用阴影；层级优先依靠明度、间距和排版，覆盖层仅保留识别层级所必需的表面与遮罩。
- 所有路由只能通过 `BasicLayout` 获得唯一的 Header、`.content-shell` main、Footer、跳过链接与站内导航历史；页面和内容框架不得绕过它重复创建页面级 Header、main 或根内容容器。80px Header、main/footer 与认证页统一复用 `.content-shell = min(calc(100% - 160px), 1376px)`，保证品牌、导航、欢迎页 Hero 和认证双栏处在同一条对齐线上。`body` 保留常驻纵向滚动容器，Radix 覆盖层独占滚动锁和滚动条宽度补偿；不得再设置第二套根 `scrollbar-gutter` 或覆盖 `data-scroll-locked`。Header 异步账户区域必须使用固定宽度槽位，页面长短和认证恢复不得改变导航几何。Header 品牌标识使用 32px，品牌文字使用 17px，桌面导航文字保持 15px、控件至少 44px 高。认证页继续保留无外框双栏内容，但左侧主张必须复用 `.editorial-title`，右侧表单在共享 main 网格内收窄到 440px；不足 `lg` 时隐藏介绍栏。641–1023px 时全部页面两侧各 32px；不超过 640px 时两侧各 16px。网格只负责对齐，不得被渲染成可见应用外壳。
- 字体统一为自托管 Geist Sans/Mono，中文按 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei`、系统无衬线顺序回退。正文、标题、控件、表格、KPI、日期、数量、百分比、时长和文件大小使用 Geist Sans；Geist Mono 仅用于代码、命令、路径、原始 token、精确时间戳和短操作标识。可比较数字使用 `tabular-nums`，桌面表格的数值表头和单元格共同右对齐。首页编辑式标题复用 `.editorial-title`；编号 `.eyebrow` 仅用于首页真实流程步骤，普通内页、错误和空状态不得增加重复眉题或装饰标签。

### 控件、组件与交互

- 基础控件的 hover、active、loading、展开和选中状态不得改变外部几何尺寸或在文档流中位移；Button、Link 与 Radix Trigger 只过渡颜色、透明度及覆盖层属性，异步内容使用固定尺寸槽位。`asChild` 只负责组合语义与行为，不得传播会让触发器抖动的共享 transform。

- 页面根、标题区、筛选区、列表区和表单区禁止可见 Card 外壳、装饰性 border/ring、重阴影和大面积圆角容器。Input、Select、Button 等默认使用无边框实心中性表面；内容分组只使用必要的 1px 发丝 Separator。错误边界、键盘焦点轮廓和 Radix 覆盖层边界属于功能反馈，不得以“无边框”为由移除。
- 交互原语优先组合 `frontend/src/components/ui/` 中 shadcn/ui `radix-nova` 源码与 Radix UI。Dialog、AlertDialog、Sheet、Select、Dropdown Menu、Tabs、RadioGroup、Progress、Tooltip 等必须保留语义、焦点圈定、Escape 行为和触发器焦点恢复；不得用可点击 `div`、自制浮层或第二套基础组件绕过这些能力。
- 功能图标只使用 `@phosphor-icons/react` 的同一家族，并提供可访问名称；品牌标识统一通过 Next.js `Image` 使用已经设计好的 `frontend/public/logo.svg`。禁止用 emoji、文本符号、CSS 图形、临时手绘 SVG 或混用图标库代替业务图标。
- `Badge` 和胶囊只表达状态、身份、选择或交互；能力、分类、评分、尝试次数等普通元数据使用辅助文字与 `·` 分隔。空状态默认不放装饰性圆角图标 tile；图标必须提供标题之外的独立语义，否则直接省略。
- 所有已认证的非首页页面与多步骤流程必须提供明确、可键盘操作的返回路径。返回上一步优先遵循由应用记录的站内浏览历史，并为无可用历史的直接访问提供稳定站内 fallback；登录与注册不渲染通用历史返回，改用彼此之间的明确交叉链接和校验后的 `redirect`，避免过期受保护页面参与回退并形成认证循环。不得让用户只能依赖浏览器工具栏，也不得用硬编码跳转破坏正常返回链路。
- 首页格式选择必须用 Radix RadioGroup 渲染 API 返回的真实 `MediaFormat`。界面不得虚构后端没有的画质预设、字幕、容器、音频模式、文件大小、播放能力或任务状态。

### 响应式、状态与可访问性

- 390×844 是强制移动验收视口，桌面同时覆盖 1280px 与方案稿桌面尺寸。页面不得产生横向滚动；固定尺寸必须受 `max-width: 100%` 约束。移动端重排信息而非缩放桌面：导航进入 Sheet，输入/主操作纵向满宽，媒体与格式单列，表格转换为可读 Item，Dialog/Sheet 内容可滚动。
- 每个异步流程都必须设计并验证初始、加载、成功、空、校验失败、请求失败、禁用和重试状态；状态不能只靠颜色表达，也不得用空白区域冒充失败或无数据。轮询状态通过节流的 `aria-live` 播报，避免每次刷新重复朗读。
- 目标为 WCAG 2.2 AA：语义化结构、唯一 `h1`、顺序标题、真实 label/button/table、正文至少 4.5:1 对比度、可见 `2px` 焦点环与 `2px` 偏移、至少 44×44px 触控目标、完整键盘路径、准确图片替代文本，并遵循 `prefers-reduced-motion`。Tooltip 不能承载唯一必要信息。
- 生产界面优先使用真实媒体封面；失败时显示准确的不可用状态。视觉回归专用山景资产固定为 `frontend/public/images/media-preview-mountain.webp`，新增位图必须按显示尺寸裁切并优先压缩为 WebP/AVIF，禁止提交无用途原图、外链热链、伪造业务数据或仅用于装饰的大图。

### 禁止事项与变更门禁

- 禁止恢复侧栏后台壳、卡片堆叠、三步向导、高密度工具栏、渐变炫光、玻璃拟态、重投影或蓝色企业后台视觉；禁止重新引入 Ant Design、Ant Design Pro、Umi、Less、CSS-in-JS 或平行主题系统。
- 修改颜色、字体、圆角、网格、断点或基础控件时，必须同步更新 `globals.css`、[前端视觉系统设计](docs/design/frontend-visual-system.md) 和必要测试；修改导航模式或核心页面信息层级时，必须同步更新该设计文档与必要测试。视觉基准变化还必须重做 [design-qa.md](design-qa.md) 的桌面/390px 同状态比较。
- 交付前至少运行前端 `npm run lint`、`npm test`、`npm run build`，并实际检查键盘返回路径、明暗主题、加载/空/错误状态、Radix 覆盖层和页面级横向溢出。视觉 QA 只有在没有剩余 P0/P1/P2 差异且 `design-qa.md` 写明 `final result: passed` 时才算通过；QA 截图不能替代功能和无障碍验证。

## 架构与数据边界

- 后端依赖方向为 `api/workers → application → domain`。`domain` 不得导入 FastAPI、SQLAlchemy、RabbitMQ、MinIO、yt-dlp、FFmpeg 或模型 SDK。
- API、下载 Worker、媒体 Runner、AI Worker 是独立进程。PostgreSQL 是状态事实来源；跨 PostgreSQL/RabbitMQ 使用 transactional outbox，消费者必须支持幂等和 lease/heartbeat。
- PostgreSQL 只通过 `backend/sql/schema.sql` 维护当前态结构。`docker-compose-env.yml` 提供本项目专用的 PostgreSQL、RabbitMQ、Valkey、MinIO 及一次性初始化服务；复用已有基础环境时，部署者必须保证这些服务已完成同等初始化，并在启动业务容器前幂等执行该 SQL。项目不维护迁移目录、历史 schema 或旧版本兼容逻辑。结构变化时同步更新可重复执行的当前态 SQL、ORM 和测试，并同时使用空数据库与已有当前态数据库验证。
- OpenAPI 是前后端接口契约的唯一来源，通过 `/openapi.json` 提供，并由 `/docs` 展示 Swagger UI；不维护平行 DTO、手写生成类型或旧 API 适配层。
- 只实现当前需求，不添加旧目录、旧 API、旧 Provider 或旧数据库的兼容分支。单个源码文件原则上不超过 200 行，超过时按职责拆分。

## 安全与运行约束

- 仅处理用户有权下载和分析的内容。匿名 Provider 默认只处理能够正向证明为公开、免费、非 DRM 的 HTTP(S) 内容；受平台权益或媒体保护的内容只有在官方授权 Provider/Connector 按资产明确返回下载或导出授权，且输出未加密时才可生成 Artifact。Edge Agent 只能传输用户已经合法取得并显式选择的 clear 文件与脱敏声明，不得访问平台会话、网络流量、缓存或保护材料，也不得生成客户端签名、取得内容密钥或转换受保护媒体。不得借技术路径扩张会员/购买、private、follow-only 或地域权益；私网 URL、任意 yt-dlp 参数和 shell 输入始终禁止。普通业务 JSON 禁止上传原始 Cookie；受控 Provider 会话只能按 005 的 allowlist、独立 Runner、只读 Secret、权益防火墙和验收门禁启用。
- 匿名媒体流量只能由无 Provider 凭据的 Runner 发起；凭据 Runner 只能获得单 Provider、版本化的只读会话 Secret，不得获得数据库、队列、对象存储或 AI 凭据。两类 Runner 均须经过阻断私网的 egress proxy；入口 URL 校验不能替代网络隔离。
- Worker 开工前重新解析语义下载计划；Provider format id 不能作为唯一恢复依据。
- AI 任务独立于下载任务；AI 失败不得改变下载成功状态。模型输出必须通过严格 schema、连续分镜时间轴和 shot evidence 校验，普通日志不得记录完整 Prompt、抽帧或原始模型响应。
- 基础设施 Secret 只来自类型化配置和环境变量；管理员在 Web 中维护的 AI Provider Key 只允许进入记录绑定的加密数据库字段，并仅在 Analysis Worker 内存中解密。任何 Secret 都不得进入前端、API 响应、异常、快照、测试夹具或普通日志。外部操作必须设置大小、时长、并发和超时上限，取消时终止整个子进程组。
- 复用本机 OAuth 的 AI Worker 是 Compose 完整拓扑的唯一例外：必须由已登录 Codex 或 Claude CLI 的宿主机用户启动，容器不得挂载或复制 CLI 认证目录。
- Compose 必须保持职责清晰：`docker-compose-env.yml` 只定义本项目基础环境及其一次性初始化，`docker-compose.yml` 只定义本机业务、Worker、Runner 和出口代理，`docker-compose-prod.yml` 只定义生产业务差异；不新增仅供 CI 或单个开发者使用的覆盖文件。业务 Compose 通过 `.env` 中的 `POSTGRES_HOST/PORT`、`RABBITMQ_HOST/PORT`、`VALKEY_HOST/PORT` 和 `MINIO_HOST/PORT` 连接基础环境：组合环境 Compose 时使用服务名和容器端口，复用已有基础环境时使用宿主机可达地址和已发布端口。`HOST_*_PORT` 只用于环境 Compose 的宿主机端口发布。MinIO 全部业务进程只共用一组 `MINIO_ACCESS_KEY` 与 `MINIO_SECRET_KEY`。所有服务必须显式设置稳定的 `container_name`。启动前按需复制 `.env.example` 为 `.env`，生产环境复制 `.env.prod.example` 为 `.env.prod` 并替换占位值。不要提交 `.env`、制品、缓存、日志、临时目录、虚拟环境或 `node_modules/`。

## 实现与验证

- 修改前先阅读相邻代码、对应 README 和测试，优先复用现有模型、端口、组件与工具函数。
- 删除失效文件、引用、依赖和文档，不保留“以后可能使用”的空目录、转发层或重复实现。
- 根据改动范围执行最小充分验证；修复缺陷时补充能稳定复现问题的测试。
- GitHub Actions 工作流直接执行仓库、后端、前端和 Compose 运行边界门禁；下列命令是各模块的本地检查入口。
- 后端命令从 `backend/` 执行：

```bash
uv sync --frozen --dev
uv run ruff check app tests
uv run mypy app
uv run pytest
```

- 前端命令从 `frontend/` 执行：

```bash
npm ci
npm run lint
npm test
npm run build
```

- 涉及接口契约时验证 OpenAPI 生成结果和前后端契约测试；涉及运行时、依赖或容器时分别验证环境 Compose、业务 Compose 和生产 Compose 可以解析，按需验证镜像构建和关键健康接口。
- 不得隐瞒失败的检查。无法在当前平台完成的验证应在交付说明中写明原因、已执行范围和剩余风险。

## 文档规范

- 根 `README.md` 说明仓库入口和运行方式；`backend/README.md`、`frontend/README.md` 说明模块用法；详细事实放在 `docs/`，不要在多个文件复制大段内容。
- 功能资料按 `Design → PRD → Plan → Acceptance` 维护。架构、目录、命令、配置或验收状态变化时，同步更新对应文档。
- 未完成文档分别直接维护在 `docs/design/`、`docs/prd/`、`docs/plans/`、`docs/acceptance/`。完成真实验收后先判断是否仍包含需要在仓库中持续维护的决策或验收事实：纯实施过程且当前事实已合并到长期文档的，直接删除完整四件套并通过 Git 历史追溯；仍有长期查阅价值的，才按类型同时迁入 `docs/design/archive/`、`docs/prd/archive/`、`docs/plans/archive/`、`docs/acceptance/archive/`。
- 禁止使用集中式 `docs/archive/`、按编号建立归档目录、只处理四件套中的部分文档，或为纯过程文件建立归档。删除或归档时必须在同一变更中同步 `docs/README.md`、状态码和仓库内全部引用。
- 文档只描述当前真实实现；历史方案通过 Git 追溯，不保留已废弃内容作为“兼容说明”。

## Git 与任务交付

- 开始任务和提交前都执行 `git status --short`，识别并保留用户已有改动；不得覆盖、删除或顺带提交与当前任务无关的文件。
- 一个“小任务”应是可独立说明、可独立验证、可安全回滚的一组改动。完成并通过相关检查后立即提交，不把多个无关任务积累到同一提交。
- 提交信息建议使用 Conventional Commits，格式为 `<type>(<scope>): <中文描述>`；不需要作用域时使用 `<type>: <中文描述>`，禁止使用空作用域 `feat(): ...`。提交说明只服务于协作可读性，不作为 GitHub Actions 的 CI 阻断条件。
- `type` 使用小写英文：新功能 `feat`、缺陷修复 `fix`、重构 `refactor`、文档 `docs`、测试 `test`、性能 `perf`、构建 `build`、持续集成 `ci`、维护 `chore`、纯格式 `style`、回退 `revert`。
- `scope` 使用稳定且非空的小写英文模块名，例如 `api`、`frontend`、`backend`、`runner`、`worker`、`docs` 或 `deps`；无法准确归属时省略作用域，不得临时发明含糊缩写。
- 冒号后使用简洁、明确的中文动作描述，不加句号，例如 `feat(api): 增加下载任务取消接口`、`fix(frontend): 修复任务状态轮询泄漏`、`docs: 补充本地开发说明`。
- 破坏性变更在类型或作用域后添加 `!`，例如 `feat(api)!: 移除旧下载接口`，并在提交正文中使用 `BREAKING CHANGE: <中文说明>` 描述迁移影响。
- 提交前检查暂存区，只暂存当前任务文件；禁止提交 Secret、缓存、构建产物、日志、临时文件或无意义格式化改动。
- 提交完成后再次执行 `git status --short`，正常情况下工作区必须为空。若任务开始时已有用户未提交改动，应原样保留并在交付时明确说明，不能为了“干净”而擅自清理。
- 只有用户明确要求时才推送远端、创建分支或发起 PR。不得擅自改写已有提交、强制推送或使用破坏性 Git 操作。
- 最终交付说明使用中文，至少包含修改摘要、验证结果、提交哈希和工作区状态；存在未完成项或已知风险时必须明确列出。
