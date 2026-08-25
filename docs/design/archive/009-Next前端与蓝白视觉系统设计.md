# 009 Next 前端与 Vercel 式无边框视觉系统设计

- 状态：Accepted
- 日期：2026-08-09
- 视觉基准：用户选定的 Product Design 方案 3 无边框修订稿（`/Users/stephenqiu/.codex/generated_images/019fe657-3556-7102-a4d8-f0f95698076b/exec-6ad65a6b-a139-48c1-a789-730a53116807.png`，1487×1058）
- 风格参考：[Vercel 首页](https://vercel.com/home)、[Geist 设计系统](https://vercel.com/geist)、[Geist 排版](https://vercel.com/geist/typography)

## 目标与边界

前端整体迁移为 Next.js App Router，并以 shadcn/ui `radix-nova`、Radix UI、Tailwind CSS 和 `@umijs/openapi` 组成唯一前端技术栈。最终代码不再保留 Umi Max、Ant Design、Ant Design Pro、Less 或平行路由器。迁移覆盖当前全部用户能力，不改动下载、AI 分析、认证和用户管理的业务语义。

视觉以方案 3 为布局、文案与信息层级的第一依据：`#FAFAFA` 偏白画布、大尺寸编辑式 Hero、大留白、无侧栏、近黑前景与主操作，内容本身而不是卡片框架构成页面结构。Vercel/Geist 提供 80px 无边框导航、Header/内容统一隐形网格、克制的中性色与密度稳定的排版节奏。控件使用无边框填充面，只在内容分组确有需要时使用 1px 发丝分隔。

交互和内容容器优先使用 [shadcn/ui 组件](https://ui.shadcn.com/docs/components)的 `radix-nova` 源码组合，并保留 [Radix 无障碍行为](https://www.radix-ui.com/primitives/docs/overview/accessibility)。shadcn 是项目内可审计的组件源码而不是平行运行时 UI 框架，页面不得另建第二套基础组件。

不在本次范围内新增视频平台、支付、社交登录或后端业务接口。明暗主题跟随系统偏好并只消费现有语义 token；页面不提供可见主题切换器，也不改变业务语义。生产环境仍不运行 Next.js Node 服务，FastAPI 继续同源提供静态页面与 `/api/*`。

## 设计依据与冲突优先级

1. 用户选定的方案 3 决定首页桌面端布局、视觉节奏、核心文案和主流程信息层级。
2. 本文决定技术边界、交互状态、响应式、可访问性与其他路由如何延续同一视觉语言。
3. Vercel 首页和 Geist 决定 80px 无边框 Header、浅色网格、大留白、短句式内容和低装饰密度等原则。
4. 旧前端只作为功能清单与接口行为参考，不延续 Ant Design Pro 的后台壳、卡片堆叠或视觉 token。

当参考之间冲突时按以上顺序执行。不得为了“更像后台系统”恢复侧栏、重卡片或高密度工具栏。

## 技术架构决策

| 层级 | 唯一选型 | 约束 |
| --- | --- | --- |
| 路由与构建 | Next.js App Router | 使用 `src/app/`、静态导出和路由组；不使用 Pages Router、Umi 路由或 Next 运行时服务 |
| UI 原语 | shadcn/ui `radix-nova` + Radix UI | 使用官方 registry 源码和语义 token；Dialog、Dropdown Menu、Select、Tabs、Progress、Sheet、Tooltip、AlertDialog 等交互保留 Radix 语义与焦点行为 |
| 样式 | Tailwind CSS | 全局 token 由 CSS 变量定义，组件只消费语义类；不新增 Less、CSS-in-JS 或另一套主题系统 |
| 图标与品牌 | `@phosphor-icons/react` + `public/logo.svg` | 功能图标继续使用 Phosphor 的同一线性/填充家族；Header 品牌标识与页面 metadata 通过 Next.js `Image`/icons 使用已经设计好的 Logo；禁止用 emoji、文本符号、手绘 SVG、CSS 图形代替功能图标 |
| API 生成 | `@umijs/openapi` | 直接作为开发依赖，通过 `openapi2ts` 读取 FastAPI `/openapi.json`；不依赖 Umi Max 插件 |
| HTTP | 单一 Axios 封装 | 生成服务统一导入 `src/lib/request.ts`；业务页面不得直接拼接请求或重复声明 DTO |
| 测试 | Vitest + Testing Library + 浏览器端 E2E/axe | 验证功能、路由、键盘操作、390px 布局和视觉基准 |

推荐目录职责如下：

```text
frontend/src/
├── app/
│   ├── page.tsx
│   ├── history/page.tsx
│   ├── account/page.tsx
│   ├── admin/users/page.tsx
│   ├── admin/analytics/page.tsx
│   ├── downloads/detail/page.tsx
│   ├── user/login/page.tsx
│   ├── user/register/page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── not-found.tsx
├── components/
│   ├── ui/                 Radix 原语的项目级封装
│   └── ...                 下载、历史、分析、用户管理组件
├── hooks/                  认证、轮询与任务状态
├── lib/                    request、请求错误、鉴权恢复与通用工具
└── services/
    ├── video/              OpenAPI 自动生成，禁止手改
    └── ...                 薄业务适配层
```

App Router 页面默认保持可静态渲染；只有表单、菜单、选择器、轮询和任务操作等交互边界使用 `'use client'`。认证用户数据由浏览器加载，不把 Cookie、用户资料或任务状态写入静态 HTML。

## 路由与访问控制

| 用户地址 | App Router 页面 | 权限 | 说明 |
| --- | --- | --- | --- |
| `/` | `app/page.tsx` | 已登录 | 解析链接、选择格式并创建下载任务 |
| `/history` | `app/history/page.tsx` | 已登录 | 搜索、筛选、分页、打开任务或获取文件 |
| `/documents` | `app/documents/page.tsx` | 已登录 | 分页查看剧本文档的解析状态与提取规模 |
| `/documents/detail?documentId=<id>` | `app/documents/detail/page.tsx` | 已登录且拥有文档 | 核对文档元数据、质量警告与有界纯文本预览 |
| `/account` | `app/account/page.tsx` | 已登录 | 查看邮箱与身份、修改用户名 |
| `/admin/users` | `app/admin/users/page.tsx` | 管理员 | 搜索、筛选、分页并更新他人角色/启用状态 |
| `/admin/analytics` | `app/admin/analytics/page.tsx` | 管理员 | 查看 7/30/90 天下载摘要、日趋势与视频来源分布 |
| `/admin/providers` | `app/admin/providers/page.tsx` | 管理员 | 维护平台状态页名称、排序与可见性，不修改系统下载能力 |
| `/downloads/detail?jobId=<id>` | `app/downloads/detail/page.tsx` | 已登录且拥有任务 | 下载状态、取消/取件、AI 视觉分镜、高光与资产；静态导出的 canonical 地址 |
| `/user/login` | `app/user/login/page.tsx` | 公开 | 登录并返回经过校验的站内 `redirect` |
| `/user/register` | `app/user/register/page.tsx` | 公开 | 注册并返回经过校验的站内 `redirect` |
| `/downloads/{jobId}` | FastAPI 308 | 与目标页一致 | 旧详情地址永久重定向到 `/downloads/detail?jobId=<id>` |
| 其他地址 | `not-found.tsx` | 公开 | 返回静态 404 页面，不伪装为成功首页 |

Next.js `output: "export"` 无法为未知任务 ID 枚举 `/downloads/[jobId]` 静态页面，因此动态段不进入目标路由树。FastAPI 必须在静态挂载前匹配旧地址并进行安全 URL 编码的 308 重定向；`/downloads/detail` 必须先于该兼容规则匹配。前端创建任务、历史入口和内部链接全部直接生成 canonical 地址。

`(app)` 布局使用客户端 Auth Boundary 调用 `/api/auth/me`。恢复会话期间显示稳定骨架；401 只允许跳转到 `/user/login?redirect=<站内地址>`，管理员页面还需校验最新角色。重定向参数必须拒绝绝对 URL、协议相对 URL、反斜杠和认证页自循环。

## 静态导出与 FastAPI 同源

- `next.config` 使用 `output: "export"`、`trailingSlash: true`；远程视频封面使用普通响应式图片或 `images.unoptimized`，不依赖 Next Image Optimization 服务。
- 构建产物固定为 `frontend/out/`。根 Dockerfile 只复制该目录到运行镜像，运行时不包含 `next start` 或独立 Node 前端进程。
- FastAPI 从 `FRONTEND_DIST_DIR` 同源提供导出文件。`/api`、`/health`、`/docs`、`/redoc`、`/openapi.json` 永远由后端处理，缺失接口不得回退 HTML。
- 已导出的页面支持直接打开和浏览器刷新；未知 UI 地址返回 `404.html` 与 HTTP 404。静态资源使用内容哈希和长缓存，HTML 使用可重新验证的缓存策略。
- 浏览器生产请求全部使用相对地址；访问令牌或 Refresh 凭据不得进入 URL、localStorage、构建变量或静态文件。
- 本地 Next 开发如需代理，只能在开发模式条件下把 `/api/*`、`/health/*` 和 OpenAPI 文档地址转发到 FastAPI；生产构建配置不得包含静态导出不支持的 rewrite。

不得引入 Server Actions、Route Handlers、请求时 Server Components、Middleware、ISR 或其他需要 Next 服务端运行时的能力。

## OpenAPI 唯一契约

FastAPI `/openapi.json` 是请求、响应与错误字段的唯一事实来源。后端每个公开操作必须提供稳定且全局唯一的 `operationId` 与明确 tag；契约测试应在生成前拒绝缺失或重复 ID。

`frontend/openapi2ts.config.ts` 直接配置 `@umijs/openapi`：

- schema 默认读取已启动 FastAPI 的 `http://127.0.0.1:8101/openapi.json`，CI 可通过环境变量指向由同一 FastAPI 应用临时导出的 JSON；该临时文件不作为第二份契约提交。
- 生成目录固定为 `src/services/video/`，namespace 固定为 `API`，请求导入固定指向 `src/lib/request.ts`。
- `npm run openapi` 是唯一生成入口；生成目录禁止手工修改。
- 页面通过生成函数或薄业务适配层调用接口，不手写重复 DTO、旧接口兼容器或另一套 schema。
- CI 重新生成后必须无 Git 差异，以证明提交的客户端与当前后端契约一致。

请求封装统一处理同源 Cookie、错误模型、一次 Refresh 会话轮换、并发刷新合并和失败后的登录跳转。轮询与取消语义放在 hooks，不散落到页面组件。

## Vercel 式无边框视觉系统

### 色彩 token

| Token | 值 | 用途 |
| --- | --- | --- |
| `--background` | `#FAFAFA` | 页面主画布，对应 Vercel/Geist 浅色内容背景 |
| `--card` | `#FFFFFF` | 仅供 Popover、Dialog、Sheet 等覆盖层分层；页面内不显示 Card 外壳 |
| `--foreground` | `#0A0A0A` | 正文与标题 |
| `--muted-foreground` | `#686868` | 次要说明与元数据 |
| `--primary` | `#111111` | 主操作与高强调填充面 |
| `--primary-hover` | `#2B2B2B` | 主操作悬停 |
| `--ring` | `#111111` | 键盘焦点轮廓，不用作装饰 ring |
| `--surface` | `#F5F5F5` | 无边框次级控件与静默区域的填充面 |
| `--border` | `#E6E6E6` | 仅用于内容节奏所需的 1px 发丝分隔与功能边界 |
| `--success` | `#16824D` | 成功状态 |
| `--warning` | `#854D0E` | 等待与重试状态；与 10% warning 填充组合满足普通文字 AA 对比度 |
| `--destructive` | `#DC2626` | 错误与破坏性操作 |

颜色必须通过语义 token 使用。主按钮使用近黑填充与白字，链接、焦点和选中态也优先使用中性色和形状/文字变化。状态不能只靠颜色表达，必须同时包含文字或图标。

### 字体、间距与容器

- 字体栈以 Next.js 自托管 Geist Sans 为西文与数字基线，中文依次回退到 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei` 与系统无衬线字体；运行时不从第三方加载字体。尺度参考 [Geist Typography](https://vercel.com/geist/typography)：首页 H1 使用随视口流动的大尺寸编辑式尺度与紧凑行高；内页根据信息密度使用同一响应式标题阶梯，不再强制旧的 32px/28px 固定页标尺寸。
- 正文、标题、控件、表头、日期、KPI、数量、百分比、时长和文件大小都使用 Geist Sans；Geist Mono 只用于代码、命令、路径、原始 token、精确时间戳以及目录键、来源键等短操作标识。数字比较使用 `tabular-nums`，不因内容为数字而自动改成等宽字体。桌面表格的数值表头和单元格统一右对齐，移动端转为 Item 摘要。
- Header、常规 main 与 footer 统一使用 `.content-shell = min(calc(100% - 160px), 1376px)`，让品牌、导航操作和页面主体共享左右对齐线。`body` 作为始终可见的纵向滚动容器，稳定长短页面切换；页面根节点不额外设置 `scrollbar-gutter`，滚动锁与滚动条宽度补偿统一交给 Radix 覆盖层原语。Dropdown、Dialog、Select 和 Sheet 不得再引入第二套全局补偿或覆盖 `data-scroll-locked`，避免同一滚动条被重复计算而让整页抖动。Header 内的认证账户区域使用固定宽度槽位，加载占位、登录入口与 Avatar 菜单切换时不得重排其他导航项。认证页的无外框双栏 main 是唯一例外，可使用更宽的 `.page-shell = min(calc(100% - 80px), 1456px)`，右侧表单在内部收窄到 440px，不足 `lg` 时隐藏介绍栏。在 641–1023px，`.content-shell` 改为两侧各 32px gutter；在 `<=640px`，`.page-shell` 与 `.content-shell` 都改为两侧各 16px gutter。这是对齐约束，不得呈现为可见页面外壳；资料表单、说明文字和媒体可在对应网格内二次收窄。
- 间距采用 4px 基准，控件内部使用 8/12/16px，内容组使用 24/32px，主要段落使用 48/64/96px。标题、描述和主操作之间必须保留明显层级，不通过额外卡片填满空白。除首页、认证双栏和垂直居中的 404 外，常规内页与任务缺失状态统一复用 `.inner-page`：移动端上下各 24px、641px 及以上各 32px；页面不得再自行叠加 `py-20`/`py-24`，避免 80px Header 后出现第二段近似 Header 高度的空档。`BackLink` 与 PageHeader 之间固定使用 16px 紧凑节奏，标题区之后再按内容语义使用 40/48/64px 分组间距。首页编辑式 Hero 作为唯一内容页例外，导航后使用移动 40px、平板 48px、桌面 56px 的渐进留白。
- 内页标题保持短、直接并与首页共用 Geist 层级；默认不使用编号 eyebrow、装饰性彩色分类标签或与 H1 重复的说明。真实流程顺序由任务状态和内容结构表达，不在标题前附加装饰编号。
- Header 视觉高度为 80px，与 main/footer 共用 `.content-shell` 的桌面 80px gutter 和 1376px 最大宽度。品牌标识为 32px，品牌文字为 17px，桌面导航文字为 15px，导航控件高度为 44px，以明确的品牌层级与宽屏主体保持稳定的视觉比例。Header 本身不使用下边线、外框、ring 或阴影。
- 页面根、标题区、筛选区、列表区和表单区不使用可见 Card 外壳、装饰 ring、阴影或装饰性大边框。输入、选择器和按钮优先用实心中性填充面与颜色对比建立边界；内容分组只使用必要的 1px 发丝 Separator。Dialog、Sheet、Popover 等 Radix 覆盖层仍保留可辨识表面、遮罩、焦点圈定和 Escape/焦点恢复。键盘焦点轮廓是功能性边界，不属于装饰 ring。
- Button、Link 与 Radix Trigger 的 hover、active、loading、展开和选中反馈只改变颜色、透明度或不参与文档流的覆盖层，不得通过 `top`、`left`、margin、尺寸或 translate 改变控件几何；异步状态切换必须保留稳定外框与必要的图标、账户占位槽。
- 动效以 120–200ms 的透明度或位移过渡为主，并遵循 `prefers-reduced-motion`。

“无边框”指移除应用壳、卡片、控件轮廓和区域的装饰性边框；不影响 Separator、错误表达和可见键盘焦点等功能性边界。

### 官方组件映射

`frontend/components.json` 固定使用 shadcn `radix-nova`、Radix base、neutral base color 与 CSS variables。页面先选下表官方组件，只在业务组合层补充文案、请求和状态转换：

| 信息/交互语义 | 官方组件 | 项目使用规则 |
| --- | --- | --- |
| 页内内容分组 | 语义化 section + [Separator](https://ui.shadcn.com/docs/components/radix/separator) | 不呈现 Card 外壳；通过排版、留白和必要的 1px 发丝线分组 |
| 桌面数据 | [Table](https://ui.shadcn.com/docs/components/radix/table) | 用于管理员用户列表和下载分析的精确数值；保留 `caption`、列头和行语义，数值表头/单元格共同右对齐并使用 `tabular-nums`，390px 下切换为 Item/摘要列表 |
| 数据可视化 | 语义化 `figure` + 响应式图表 | 图表有可读标题和等价表格/列表；数值不只靠颜色或 Tooltip 传达，不增加 Card 外壳 |
| 移动导航/补充内容 | [Sheet](https://ui.shadcn.com/docs/components/radix/sheet) | 从右侧进入，标题与描述可读，关闭后焦点返回触发器 |
| 图标辅助说明 | [Tooltip](https://ui.shadcn.com/docs/components/radix/tooltip) | 只补充说明，不承载唯一必要信息；支持 hover 与键盘 focus |
| 用户身份 | [Avatar](https://ui.shadcn.com/docs/components/radix/avatar) | 必须有稳定 fallback，同时保留可读用户名 |
| 表单字段 | [Field](https://ui.shadcn.com/docs/components/radix/field) + [Input Group](https://ui.shadcn.com/docs/components/radix/input-group) | 统一 label、description、error 关联；前后图标或清除动作放入 InputGroup |
| 记录/结果项 | [Item](https://ui.shadcn.com/docs/components/radix/item) | 历史在桌面与移动端均使用 Item/ItemGroup，也用于管理员移动列表；主信息、元数据和操作顺序固定 |
| 无数据 | [Empty](https://ui.shadcn.com/docs/components/radix/empty) | 包含状态名、一句原因和至多一个主恢复动作；默认不放无额外含义的圆角图标 tile |
| 分页 | [Pagination](https://ui.shadcn.com/docs/components/radix/pagination) | 有当前页语义和可读名称；390px 优先上/下页而非完整页码 |
| 破坏性确认 | [Alert Dialog](https://ui.shadcn.com/docs/components/radix/alert-dialog) | 仅用于取消下载和取消分析；取消为安全默认，明确后果，管理员编辑仍在普通 Dialog 中完成 |
| 媒体尺寸 | [Aspect Ratio](https://ui.shadcn.com/docs/components/radix/aspect-ratio) | 缩略图和预览固定 1.86:1，加载失败也不造成布局塌陷 |

布局所需的 Separator、Badge、Button、Select、Dropdown Menu、Dialog、Tabs、Progress、Skeleton、Spinner 同样复用 registry 实现。Badge 与胶囊只表示状态、身份、选择或交互；平台能力、镜头属性、资产类型、评分、尝试次数等普通元数据使用辅助文字和 `·` 分隔。页面可以用 Tailwind 排列组件，但不得绕过它们另造不具备语义和焦点行为的可点击 `div`。

## 页面设计

### 全局导航

桌面端为 80px 单行轻量 Header：左侧使用 Next.js `Image` 渲染 32px 的 `public/logo.svg`，与 17px 文字“帧取”共同构成指向 `/` 的品牌链接；右侧导航保持 15px 尺寸，桌面导航控件高度为 44px，使品牌在功能导航之上建立清晰层级。右侧依次提供“首页”“下载记录”（`href="/history"`）、“剧本文档”（`href="/documents"`）、“平台状态”和 Avatar 账户菜单；账户菜单只向管理员显示“用户管理”“平台目录”与“下载分析”入口。明暗主题跟随系统偏好，不在 Header 或菜单里增加可见切换器。Header 与 main 共用 `.content-shell` 的 1376px 上限和桌面 80px gutter，保持导航与主体严格对齐；没有底线、侧栏、面包屑容器、外框或浮起阴影。当前路由链接使用 `aria-current="page"`，并通过中性填充面和文本色同步表达当前页。

不足 `lg` 的窄屏与平板宽度保留品牌和一个明确的导航触发器，下载记录、剧本文档、平台状态与账户操作进入 Sheet；不把完整桌面导航强行压缩到同一行。Sheet 打开后焦点进入其可操作内容，过长时在 Sheet 内部滚动，链接均可通过 Tab 到达并以键盘激活；关闭而未导航时，焦点返回触发器。品牌链接始终提供返回 `/` 的明确可读名称。图标按钮有可见或屏幕阅读器标签，Tooltip 仅作辅助，触控区域至少 44×44px。

所有已认证的非首页页面在内容标题前提供统一 `BackLink`，文字为“返回上一步”，触控高度至少 44px。应用在当前标签页内记录最小站内导航栈：存在上一条站内记录时调用浏览器历史返回，直接打开页面或历史不可用时使用明确的层级 fallback（历史→首页、账户→首页、用户管理/下载分析→账户、下载详情/任务缺失→下载历史、404→首页）。记录使用完整的站内 pathname + search，并为浏览器历史条目分配不含业务数据的临时标记，保证 query-only 详情切换、前进/后退和重复路径都能精确定位；`sessionStorage` 仅保存这些站内路由、标记和当前索引，不包含账户、任务内容或凭据。登录与注册不显示通用历史返回，只保留彼此之间的明确交叉链接和校验后的安全 `redirect`；认证守卫继续使用 replace，避免过期受保护页面参与回退并形成登录循环。

### 首页 `/`

首页严格延续方案 3：

1. 首屏直接使用大尺寸编辑式主张“把素材，带回本地。”和一句任务说明；不使用流程编号眉题或旧的居中标题文案。
2. 主输入以 Field + InputGroup + Button 组合，InputGroup 使用浅中性实心填充，解析按钮使用近黑填充；两者都不使用装饰性边框。输入有真实 label、Phosphor 链接图标、清除动作、提交中状态和内联错误。
3. 旧的“链接 → 格式 → 下载”三步导航/进度 UI 不再出现；页面用留白、操作状态和结果内容的自然顺序表达流程。
4. 解析成功后展示媒体画面与真实格式选择双栏：媒体区使用真实封面、标题、平台和时长；选择区必须用 Radix `RadioGroup` 直接渲染 API 返回的每一个 `MediaFormat`，并展示其分辨率、容器、编码与帧率。不得伪造“最佳画质/兼容优先/仅音频”预设，不增加未由契约支持的字幕或容器选择器，也不在静态封面上放置伪播放控件。
5. 页面内不放置结果 Card 外壳；双栏只用留白和必要的发丝 Separator 组织。方案 3 中的群山湖泊媒体示例使用 `frontend/public/images/media-preview-mountain.webp`（约 221 KiB），用于稳定演示/视觉回归；生产解析成功态仍优先显示真实媒体封面。
6. 首页统一提供“链接解析 / 本地视频 / 剧本文档”三个 Tabs。移动端三个入口必须等分 `.content-shell` 的可用宽度并共享视觉中心，避免内在内容宽度让整组偏向一侧或在 320px 窄屏溢出；`sm` 及以上恢复紧凑的内容宽度线型布局。上传动作直接由文件选择和主按钮完成，不增加固定前提确认框、重复合法性说明、实现细节说明或页面底部提示；格式、大小、错误和进度只在帮助用户完成当前任务时出现。

首页必须覆盖初始、URL 校验失败、解析中、解析失败、无可用格式、已解析、创建任务中七种状态。提交不得重复创建任务，幂等键语义与旧实现一致。创建成功直接进入 canonical 详情地址。

### 下载历史 `/history`

PageHeader 直接显示“下载历史”及一句用途说明、可选的“新建下载”主操作，不在 H1 上方显示“任务记录”等重复眉题。页面顶部复用 `.inner-page` 的移动 24px、其余视口 32px 节奏，避免 80px Header 后出现第二段过长空档；搜索、状态筛选和刷新紧随标题区。桌面端与移动端均使用 Item/ItemGroup，行间只有 ItemSeparator；视频标题和封面构成第一信息层级。桌面端展开为宽行并保留更完整元数据，390px 下重排为单列，每项展示标题、格式、状态、时间和唯一主操作，不通过横向滚动隐藏内容。Pagination 在桌面端可展示页码，390px 下精简为上/下页和当前页说明。

空状态、筛选无结果、加载、刷新失败和分页均有明确文案；无数据使用左对齐的 Empty 组合，不用空 Card、装饰性插图或圆角图标底座占位。成功任务提供“获取文件”，其他任务提供“查看任务”。初始加载骨架必须为最终统计摘要保留相同的 18px 高度和上下间距，数据到达时不得把列表区域向下推移。无论列表处于加载、空、错误或正常状态，Header 中的品牌首页链接都保持可用，使用户无需依赖浏览器后退即可开始新的解析。

### 下载详情 `/downloads/detail`

页面读取并校验 `jobId` 查询参数。缺失、格式非法、无权限或不存在时使用 Empty/Alert 给出不同但不泄露敏感信息的恢复路径。统一返回入口优先回到实际上一条站内记录，直接访问时回落到 `/history`。正常态使用连续内容区：AspectRatio 封面、任务状态、操作和分析内容按阅读顺序排列，区段间使用 Separator，不包在一张 Card 中。任务详情 API 必须随持久任务返回标题、封面、时长、平台与所选语义格式；短期解析资源过期后仍由这些任务展示字段维持完整首屏，不以“封面不可用”、通用标题或格式破折号降级。完成态只在状态标题、文件保留信息与完整性说明中各表达一次结果，不重复渲染 100% 进度和“已完成”阶段。任务阶段决定取消、获取文件、开始分析、取消分析或重新分析动作；取消下载或分析使用 AlertDialog，不使用浏览器原生 `confirm`。

进度值使用文本与 Radix Progress 同时表达，并通过节流的 `aria-live="polite"` 发布关键阶段变化。AI 分析成功后展示视觉摘要、分镜、高光和资产，时间按钮为后续播放器联动保留键盘语义；下载失败不伪装为空状态，AI 失败不改变下载成功表达。

### 登录与注册

认证页使用 `.page-shell` 的无外框双栏版式：桌面左栏承载简短产品主张与合法使用提示，右栏用发丝分隔后放置不超过 440px 的表单；不足 `lg` 时隐藏介绍栏，并在可用内容区域内水平居中表单，手机宽度下再自然占满可用宽度。登录突出邮箱、密码和单一近黑主按钮；注册增加用户名与密码确认。标题使用“登录，继续下载。”或“创建账户，保存进度。”等直接动作句，不增加编号流程眉题。字段统一由 Field + InputGroup 组合 label、描述、密码可见性与错误，错误出现在对应字段附近并在提交失败时聚焦摘要。登录态用户访问认证页时返回校验后的安全站内目标；登录和注册通过明确的交叉链接互相切换，不显示可能回到过期受保护页面的通用历史返回。

### 个人资料与管理员页面

个人资料以 Avatar 身份摘要和单列 Field 表单展示可编辑用户名，以及只读邮箱和角色；PageHeader 直接显示“个人资料”，不增加“账户设置”等眉题，保存后导航名称同步更新。用户管理 PageHeader 直接显示“用户管理”，不增加“系统管理”等眉题；桌面端为 Table 与筛选条，编辑角色和状态使用普通 Dialog，不使用 AlertDialog。管理员不能修改自己的角色或启用状态，禁用原因必须可感知。平台目录采用同一桌面 Table/移动 Item 语言，编辑使用 Dialog、删除使用 AlertDialog，并以“系统已注册/仅目录”徽标明确展示安全执行能力是否存在；排序列右对齐并使用表格数字。平台状态只为验证/访问状态保留 Badge，普通能力改用辅助文字分隔；各平台描述行以稳定留白组织，不在列表外沿或行间显示分割线。

用户搜索、分页、平台目录写入后的回读、平台状态刷新和下载分析周期切换均采用保留旧内容的后台刷新：只有首次进入且没有任何可展示数据时才使用骨架或加载占位。已有 Table、ItemGroup、指标或图表不得在请求开始时卸载，也不得用行数更少的骨架临时替换；请求完成后直接提交新结果，并以 `aria-busy` 或控件禁用态表达进行中状态，避免文档高度先塌陷再恢复。

下载分析 PageHeader 直接显示“下载分析”，使用单选 Radix Toggle Group 提供 7/30/90 天周期并保留刷新操作。摘要以 Geist Sans 表格数字、留白和克制的发丝 Separator 组织，不使用指标 Card；每日趋势以低对比面积层和状态折线构成连续的“下载脉冲”，图例使用多选 Radix Toggle Group 支持键盘显隐系列，来源占比使用 Radix Progress。来源表现中的任务、成功率、用户和数据量表头/单元格共同右对齐。图表仍提供完整的等价表格/列表数值。AI 结果中的分镜、高光和资产同样使用 Tabs + Item/ItemGroup + Separator 的连续内容流，普通属性与评分不使用 Badge，不使用页面级原生按钮或逐项可见边框卡片。页面不解密或显示来源 URL，不显示用户或单任务明细。

390px 下用户管理和下载分析的精确数值转为 Item/摘要列表，图表不超出可用宽度；用户详情和编辑进入适配视口的 Sheet/Dialog，禁止依赖横向滚动查看核心数据或操作。

### 404

静态 404 使用品牌、短句和返回首页操作，不显示调试信息。FastAPI 对未知 UI 地址返回该页面和真实 404 状态。

## 响应式规范

390×844 是强制验收视口，不是事后缩放桌面布局。

- 桌面验收同时覆盖常见 1280px 宽视口与方案 3 原始 1487×1058 视口；Header 始终为 80px，并与 main/footer 统一按 `.content-shell` 的 1376px 上限和响应式 gutter 对齐，不因宽屏无限拉长行文。
- 页面不得出现横向滚动，任何固定宽度必须受 `max-width: 100%` 约束。
- 首页三个内容入口在移动端按三等分占满可用内容宽度，入口组、输入区和主操作共用 `.content-shell` 的水平中心；URL 输入与解析按钮改为上下排列，按钮满宽；结果改为单列，先展示媒体摘要，再展示真实格式与下载动作。
- 封面保持 1.86:1，不拉伸、不裁掉关键信息；长标题最多按上下文截断并保留完整可访问名称。
- 管理员桌面 Table 在 390px 下切换为 Item/摘要列表，下载分析图表响应式重排并保留等价文本数值；历史始终使用 Item/ItemGroup；筛选条、表单按钮和 Dialog/Sheet 采用移动布局；主操作满宽，操作之间至少 8px。
- Sheet 宽度不超过视口，内容过长时自身可滚动；AlertDialog 的标题、后果说明和取消/确认操作在 390px 下不被裁切。
- Pagination 优先保留上一页、当前页和下一页；Tooltip 不作为触屏用户获得必要信息的唯一方式。
- 导航、单选行、菜单、分页和关闭按钮的触控目标至少 44×44px。
- 软键盘出现时表单仍能滚动到错误字段和提交按钮，不使用遮挡内容的固定底栏。

## 可访问性规范

目标为 WCAG 2.2 AA：

- 使用 `header/nav/main/footer`、唯一 `h1`、顺序标题、真实 `form/label/button/table`；不得用可点击 `div` 代替控件。
- 正文对比度至少 4.5:1，大字至少 3:1，控件边界和焦点指示至少 3:1。
- 所有交互可仅用键盘完成；焦点顺序与视觉顺序一致。焦点环至少 2px，并与背景留出 2px 偏移。
- Radix Dialog、AlertDialog、Sheet、Select、Dropdown Menu 等保留其焦点圈定、Escape 关闭、触发器焦点恢复和语义属性，不覆盖为不可访问的自定义行为。AlertDialog 不允许用 Escape 绕过需要明确决策的确认语义。
- Radix `asChild` 按 [Composition 指南](https://www.radix-ui.com/primitives/docs/guides/composition) 组合：触发元素必须可聚焦，自定义 leaf component 必须透传 props 和 ref。Tooltip Trigger 不得使用不可聚焦容器。
- 异步加载、错误、下载/分析阶段变化使用适当的 `aria-live`，但不得在每次轮询时重复播报。
- 图片提供符合上下文的替代文本；标题已经完整描述内容时，装饰封面可使用空替代文本以避免重复。
- 图标不能单独承担名称；表单错误通过文本与 `aria-describedby` 关联；必填、禁用和当前状态不得只靠颜色。
- 支持浏览器缩放至 200%，并在 `prefers-reduced-motion` 下取消非必要动画。

## 设计 QA 门禁

首页在 1487×1058 视口、解析成功状态下与方案 3 无边框修订稿进行同状态对比；必须把参考图和实现截图放入同一比较输入，而不是分别凭记忆判断。重点核对 80px 无边框 Header、Header/main/footer 共用的 `.content-shell` 与断点 gutter、编辑式 Hero、输入/按钮填充面、媒体/格式双栏、群山湖泊封面裁切、真实 RadioGroup 格式行、Geist 排版、发丝 Separator 和留白。

全部路由还需在 1280px/方案 3 原始桌面视口和 390×844 下检查真实数据、加载、空、错误、打开菜单/Sheet/AlertDialog 等关键状态。P0/P1/P2 差异修复后重新截图比较，根目录 `design-qa.md` 只有在写明 `final result: passed` 后才可交付；剩余 P3 只能作为后续微调记录。

设计 QA 不能替代功能、静态导出、OpenAPI 漂移、axe 与键盘验收。
