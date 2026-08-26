# Frontend

本目录是“帧取”视频下载器的 Next.js App Router 前端。界面使用 Radix UI primitives 与 shadcn/ui 源码组件，样式由 Tailwind CSS 主题 token 管理；接口客户端由独立的 `@umijs/openapi` 根据 FastAPI 契约生成。生产构建静态导出到 `out/`，再由根 Dockerfile 复制到统一运行镜像的 `/app/frontend/out`，通过 FastAPI 与 `/api/*` 同源交付。

## 技术栈

- **应用框架**：Next.js App Router + React + TypeScript strict。
- **组件**：`src/components/ui/` 中的 shadcn/ui 源码，底层交互使用 Radix UI；完成态视频预览使用 Vidstack React 的默认播放器布局。
- **样式**：Tailwind CSS；颜色、间距、圆角、阴影和状态统一使用 `src/app/globals.css` 中的语义 token。
- **请求**：`src/lib/request.ts` 中的同源 Axios 实例；页面通过 `src/services/` 的稳定业务入口访问 API。
- **接口生成**：独立的 `@umijs/openapi`，配置位于 `openapi2ts.config.ts`。
- **测试与检查**：Biome、TypeScript、Vitest 和 Testing Library。
- **交付**：Next.js static export；生产环境不运行独立前端容器。

本地和镜像构建统一使用 Node.js 24 LTS 与 npm 11.19，具体范围以 `package.json` 的 `engines` 和 `packageManager` 为准，并使用仓库中的 `package-lock.json`。

## 本地开发

先启动后端 API：

```bash
cd ../backend
uv sync --frozen --dev
uv run python -m app.main
```

再启动前端：

```bash
cd ../frontend
npm ci
npm run dev
```

`app.main` 与 `npm run dev` 分别是后端和前端的模块开发入口；完整项目仍只通过
仓库根目录的业务 Compose 启动。开发服务器将 `/api/*` 和 `/health/*` 代理到
`http://127.0.0.1:8101`。浏览器请求始终使用同源相对路径，不配置浏览器可见的
后端地址或服务端密钥。

## 目录约定

```text
frontend/
├── next.config.ts             Next.js 静态导出与开发代理
├── openapi2ts.config.ts       @umijs/openapi 生成配置
├── components.json            shadcn/ui 组件与别名配置
├── postcss.config.mjs         Tailwind CSS PostCSS 配置
├── src/
│   ├── app/                   App Router 页面、布局、元数据与全局主题
│   ├── components/            按业务 feature 归类的跨页面组件
│   │   ├── account/           账户与个人信息
│   │   ├── admin/             管理后台
│   │   ├── analysis/          通用分析
│   │   ├── auth/              登录、注册与访问保护
│   │   ├── downloads/         下载历史与详情
│   │   ├── intake/            链接、视频和文件导入
│   │   ├── layout/            页面框架、导航与通用布局
│   │   ├── providers/         Provider 状态
│   │   ├── screenplay/        剧本文档、剧本分析与改写
│   │   └── ui/                shadcn/ui 源码与 Radix UI 组合组件
│   ├── hooks/                 下载、分析、认证等状态流程
│   ├── lib/                   Axios 请求基础设施与通用组件工具
│   ├── services/              稳定业务请求入口
│   │   └── video/             OpenAPI 自动生成的接口函数和类型
│   ├── types/                 前端业务类型
│   └── utils/                 格式化、校验与幂等键等无 UI 工具
└── tests/                     Vitest 与 Testing Library 测试
```

路由页面只放在 `src/app/`。业务组件必须放在 `src/components/` 下对应的 feature 目录，跨 feature 的页面框架组件放在 `layout/`，Radix/shadcn 基础组件放在 `src/components/ui/`；不要新增 Umi `pages/`、Vite 入口、平行路由器或独立的 `src/features/` 目录。

## OpenAPI 客户端

FastAPI 运行后执行：

```bash
npm run openapi
```

该命令根据 `openapi2ts.config.ts` 读取 `/openapi.json`，生成 `src/services/video/` 中的请求函数和 `API` 类型。需要临时读取其他契约地址时使用 `OPENAPI_SCHEMA_URL`，不要修改并提交本地地址。

`src/services/video/` 是生成目录，禁止手工修改，也不得维护平行 DTO 或手写 API 客户端。生成代码通过配置的 import statement 统一调用 `src/lib/request.ts`；页面应优先调用 `src/services/download.ts`、`analysis.ts`、`auth.ts`、`users.ts`、`provider-catalog.ts` 或 `system.ts` 等稳定业务入口。接口变化时先更新并启动 FastAPI，再执行 `npm run openapi`，最后提交契约对应的生成差异。

## 请求与鉴权

- Axios 使用同源相对 URL 并携带 HttpOnly Cookie；Access JWT 和 Refresh JWT 不进入 JavaScript、localStorage 或 sessionStorage。
- Access 会话失效时，请求层最多执行一次 Refresh 轮换并重试原请求，避免无限重试或并发刷新风暴。
- 未登录用户访问受保护页面时跳转登录页，并只接受经过校验的同源返回路径。
- 客户端可以隐藏管理员入口，但角色与启用状态仍由后端独立校验；前端权限判断不能成为安全边界。
- RFC Problem Details 在请求层统一映射，页面不直接展示后端内部错误、URL、令牌或 Provider 信息。

全局 `body` 使用始终可见的纵向滚动容器来稳定长短页面切换，滚动条锁定与宽度补偿统一由 Radix 覆盖层原语负责。根节点不得再通过 `scrollbar-gutter` 预留第二份槽位，也不得覆盖 `data-scroll-locked` 的运行时样式；Dropdown、Dialog、Select 和 Sheet 共用同一套滚动锁编排，避免重复补偿引发整页横向抖动。

## 静态导出与同源交付

`npm run build` 使用 Next.js static export 生成 `out/`。根 Dockerfile 将该目录复制到 `/app/frontend/out`，FastAPI 在 API 与健康检查路由之后挂载静态页面。已知路由可直接刷新，未知页面返回导出的 `404.html`；未知 `/api/*` 必须继续返回 JSON 404。

生产环境不启动 Next.js Server、独立前端容器或额外反向代理。需要服务端运行时能力的功能必须先确认不破坏静态导出和同源交付约束。

## 组件、主题与可访问性

- 业务页面只组合已有 shadcn/ui 组件，Radix primitive 和原生交互/表单控件只能
  出现在 `src/components/ui/`；不重新实现对话框、菜单、选择器、标签页、提示或
  表单控件。`tests/unit/component-boundaries.test.ts` 必须阻止边界回退。
- 下载完成且文件仍可用时，详情页通过 Vidstack React 默认布局加载短时制品地址；播放控件、键盘交互、全屏与移动端布局由开源组件负责，业务代码不维护平行播放器 UI。
- 当前视觉基准是用户选定的 Product Design 方案 3 无边框修订稿：`/Users/stephenqiu/.codex/generated_images/019fe657-3556-7102-a4d8-f0f95698076b/exec-6ad65a6b-a139-48c1-a789-730a53116807.png`。风格贴近 Vercel Home：`#FAFAFA` 偏白画布、Geist、`#0A0A0A` 前景、`#111111` 近黑主操作、大尺寸编辑式首页 Hero 和克制的中性表面。
- Header 高 80px 且无下边线/外框/阴影。Header、main 与 footer 统一使用 `.content-shell = min(calc(100% - 160px), 1376px)`，使导航与主体对齐；认证双栏可在内部使用更宽的 `.page-shell = min(calc(100% - 80px), 1456px)`。641–1023px 时常规内容 gutter 各 32px；不超过 640px 时两种网格 gutter 均为 16px。这些是对齐约束，不能显示成页面外壳。
- 已认证应用页统一由 `src/components/basic-layout.tsx` 提供 Header、唯一 main、Footer 和跳过链接；业务页面只返回内容区，不重复创建页面级 `main` 或 `.content-shell`。main 使用 `flex-1`，Footer 在短页面贴近视口底部，长页面随内容自然出现；认证页继续使用 `AuthPageFrame` 的双栏例外。
- 首页 Hero 与内页标题使用 Geist 响应式标题阶梯，不强制旧的固定页标尺寸。只有真实流程序号可使用中性 mono eyebrow，不使用彩色装饰性分类标签或与标题重复的说明。
- 页面根、标题区、筛选区、列表区和表单区不使用可见 PageShell/Card 外壳、装饰 ring、阴影或大边框。输入、选择器和按钮优先使用无边框实心填充面；内容层级只使用必要的 1px 发丝 Separator。错误边界、可见键盘焦点轮廓与 Radix 覆盖层的表面/遮罩必须保留。
- 首页格式选择必须使用 Radix RadioGroup 直接渲染 API 返回的真实 `MediaFormat`。不使用旧三步 UI、伪画质预设、伪字幕/容器选择器或静态封面上的伪播放按钮。群山湖泊演示/回归资产位于 `public/images/media-preview-mountain.webp`（约 221 KiB），真实封面仍优先。
- 管理员下载分析页保持连续的无边框内容流，不使用指标 Card 或图表外壳。7/30/90 天周期使用单选 Radix Toggle Group；全部、成功、失败和取消趋势使用多选 Toggle Group，并以线型、文字和状态共同表达；成功率与来源占比使用 Radix Progress。趋势图可使用无描边中性表面、低对比总量面积层和末端数据点，但必须保留完整的屏幕阅读器数据表与移动摘要。
- 功能图标继续使用已有 `@phosphor-icons/react`，品牌标识通过 Next.js `Image` 复用 `public/logo.svg`，浏览器与 Apple 图标复用同组品牌资源；不用 emoji、手绘 SVG、CSS 图形或文本符号代替标准图标。
- 业务颜色和尺寸使用语义 token 与 Tailwind utility，不在页面散落近似色值、任意阴影或一次性 CSS。
- Client Component 只用于交互和浏览器 API；其余页面、布局和元数据保持 Server Component。
- 所有交互支持键盘，表单控件有可关联标签，错误和异步状态可被辅助技术感知；RadioGroup 支持标准方向键，Dialog、Sheet、Popover、Dropdown Menu 保留 Radix 焦点圈定、Escape 关闭与触发器焦点恢复；尊重 reduced motion。
- 首次加载与异步刷新必须为最终摘要、工具条和关键操作保留同尺寸槽位；Skeleton 只能替换槽位内容，不能让成功、空或错误状态把后续内容推移。
- 桌面和 390px 窄屏均不得出现页面级横向溢出，主操作、错误恢复和核心数据在两种尺寸下都必须可用。

## 页面与视觉回归

下载分析的业务组合位于 `src/components/admin-analytics/`，路由入口为 `src/app/admin/analytics/page.tsx`。修改统计周期、趋势图、来源分布或响应式表格时，至少验证以下内容：

- 单选周期和多选趋势系列可通过 Tab 与方向键操作，状态变化不会改变外部几何尺寸。
- 浅色、深色、常规桌面和 390×844 视口下，`scrollWidth` 不大于 `clientWidth`。
- 图表显隐不移除等价精确数据，颜色不是区分成功、失败和取消的唯一手段。
- 初始加载、请求失败、空数据、刷新以及真实数据状态都保留清晰恢复路径。

对应测试位于 `tests/unit/admin-analytics-page.test.tsx`。视觉系统决策与最近一次浏览器回归证据分别记录在 `../docs/design/frontend-visual-system.md` 和 `../design-qa.md`。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm ci` | 按锁文件安装依赖 |
| `npm run dev` | 启动 Next.js 开发服务器 |
| `npm run openapi` | 从 FastAPI 重新生成接口客户端 |
| `npm run lint` | 运行 Biome lint 与 TypeScript 检查 |
| `npm run format:check` | 检查代码格式 |
| `npm test` | 运行 Vitest 测试 |
| `npm run build` | 静态构建到 `out/` |
