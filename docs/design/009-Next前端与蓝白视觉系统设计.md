# 009 Next 前端与蓝白视觉系统设计

- 状态：Accepted
- 日期：2026-08-09
- 视觉基准：用户选定的 Product Design 方案 2（附件 `exec-093b654f-524e-4641-aeb6-a196aa75c23c.png`，1487×1058）
- 风格参考：[Vercel 首页](https://vercel.com/home)

## 目标与边界

前端整体迁移为 Next.js App Router，并以 Radix UI、Tailwind CSS 和 `@umijs/openapi` 组成唯一前端技术栈。最终代码不再保留 Umi Max、Ant Design、Ant Design Pro、Less 或平行路由器。迁移覆盖当前全部用户能力，不改动下载、AI 分析、认证和用户管理的业务语义。

视觉以方案 2 为布局与信息层级的第一依据：白色画布、大留白、短文案、无侧栏、弱化容器边界，内容本身而不是卡片框架构成页面结构。Vercel 首页只提供“克制导航、明确主张、连续内容流”的设计原则；色彩改用 Apple 风格蓝白体系，不复制 Vercel 的黑色主按钮或黑色主题。

不在本次范围内新增视频平台、支付、社交登录、暗色主题或后端业务接口。生产环境仍不运行 Next.js Node 服务，FastAPI 继续同源提供静态页面与 `/api/*`。

## 设计依据与冲突优先级

1. 用户选定的方案 2 决定首页桌面端布局、视觉节奏、核心文案和主流程信息层级。
2. 本文决定技术边界、交互状态、响应式、可访问性与其他路由如何延续同一视觉语言。
3. Vercel 首页决定无边框、大留白、短句式内容和低装饰密度等原则。
4. 旧前端只作为功能清单与接口行为参考，不延续 Ant Design Pro 的后台壳、卡片堆叠或视觉 token。

当参考之间冲突时按以上顺序执行。不得为了“更像后台系统”恢复侧栏、重卡片、纯黑主题或高密度工具栏。

## 技术架构决策

| 层级 | 唯一选型 | 约束 |
| --- | --- | --- |
| 路由与构建 | Next.js App Router | 使用 `src/app/`、静态导出和路由组；不使用 Pages Router、Umi 路由或 Next 运行时服务 |
| UI 原语 | Radix UI | Dialog、Dropdown Menu、Select、Tabs、Progress、Tooltip 等交互原语由 Radix 提供；业务组件在 `src/components/` 组合 |
| 样式 | Tailwind CSS | 全局 token 由 CSS 变量定义，组件只消费语义类；不新增 Less、CSS-in-JS 或另一套主题系统 |
| 图标 | Radix Icons 或经确认的同风格开源图标库 | 禁止用 emoji、文本符号、手绘 SVG、CSS 图形代替图标 |
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
├── lib/                    request、鉴权恢复、通用工具
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
| `/account` | `app/account/page.tsx` | 已登录 | 查看邮箱与身份、修改用户名 |
| `/admin/users` | `app/admin/users/page.tsx` | 管理员 | 搜索、筛选、分页并更新他人角色/启用状态 |
| `/downloads/detail?jobId=<id>` | `app/downloads/detail/page.tsx` | 已登录且拥有任务 | 下载状态、取消/取件、AI 分析与思维导图；静态导出的 canonical 地址 |
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

## 蓝白视觉系统

### 色彩 token

| Token | 值 | 用途 |
| --- | --- | --- |
| `--background` | `#FFFFFF` | 页面主画布 |
| `--foreground` | `#1D1D1F` | 正文与标题，避免纯黑成为主题色 |
| `--muted-foreground` | `#6E6E73` | 次要说明与元数据 |
| `--primary` | `#007AFF` | 主操作、当前步骤、链接与选中态 |
| `--primary-hover` | `#0077ED` | 主操作悬停 |
| `--primary-soft` | `#F2F7FF` | 选中行和弱提示背景 |
| `--divider` | `#E8E8ED` | 行分隔与内容节奏 |
| `--control-border` | `#D2D2D7` | 输入、选择器等必要的功能边界 |
| `--success` | `#248A3D` | 成功状态 |
| `--warning` | `#B25E09` | 等待与重试状态 |
| `--destructive` | `#D70015` | 错误与破坏性操作 |

颜色必须通过语义 token 使用。主按钮使用 Apple 蓝与白字，不使用纯黑主按钮、大面积黑底或装饰性渐变。状态不能只靠颜色表达，必须同时包含文字或图标。

### 字体、间距与容器

- 字体栈以 Next.js 自托管 Geist 为西文与数字基线，中文依次回退到 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei` 与系统无衬线字体；运行时不从第三方加载字体。
- 页面正文宽度上限为 1200px；头部保持宽屏呼吸感，内容左右安全区桌面端不小于 24px、390px 视口为 16px。
- 间距采用 4px 基准，主要纵向节奏使用 24/32/48/72px。标题、描述和主操作之间必须保留明显层级，不通过额外卡片填满空白。
- 默认不使用阴影。输入框、预览图、弹窗等需要边界的元素可使用 1px 发丝线和 10–14px 圆角；内容区、列表区和表单区不得每段再包一层带边框卡片。
- 动效以 120–200ms 的透明度或位移过渡为主，并遵循 `prefers-reduced-motion`。

“无边框”指移除应用壳、卡片和区域的装饰性边框，不是移除输入、表格分隔、焦点环和错误状态等必要边界。

## 页面设计

### 全局导航

桌面端为单行轻量导航：左侧品牌标识“帧取”，右侧仅保留“下载历史”和账户菜单；管理员入口位于账户菜单。没有侧栏、面包屑容器或固定黑色顶栏。当前页通过文本色、可见下划线或 `aria-current` 表达。

390px 下保留品牌和两个核心入口，次要账户操作进入 Radix Dropdown Menu。图标按钮有可见或屏幕阅读器标签，点击区域至少 44×44px。

### 首页 `/`

首页严格延续方案 2：

1. 首屏中心使用“粘贴链接，剩下的交给帧取”和一行支持平台说明，文案短而直接。
2. 主输入与“解析”按钮形成唯一视觉焦点；输入有真实 label、链接图标、清除动作、提交中状态和内联错误。
3. “01 链接 / 02 格式 / 03 下载”是进度说明，不可伪装成可点击标签；当前步骤使用蓝色和 `aria-current="step"`。
4. 解析成功后展示两栏结果：左侧为语义格式单选列表和全宽“开始下载”，右侧为真实封面、标题、平台与时长。格式行用发丝分隔和淡蓝选中面，不包独立卡片。
5. 页面底部保留合法使用提示与解析时间；不展示无关营销模块。

首页必须覆盖初始、URL 校验失败、解析中、解析失败、无可用格式、已解析、创建任务中七种状态。提交不得重复创建任务，幂等键语义与旧实现一致。创建成功直接进入 canonical 详情地址。

### 下载历史 `/history`

标题下只保留一句用途说明、搜索、状态筛选、刷新和“新建下载”。桌面端使用轻量任务列表，行间只有分隔线；视频标题和封面构成第一信息层级。移动端保持纵向任务列表，每项展示标题、格式、状态、时间和唯一主操作，不通过横向滚动隐藏内容。

空状态、筛选无结果、加载、刷新失败和分页均有明确文案。成功任务提供“获取文件”，其他任务提供“查看任务”。

### 下载详情 `/downloads/detail`

页面读取并校验 `jobId` 查询参数。缺失、格式非法、无权限或不存在时给出不同但不泄露敏感信息的恢复路径。主体先展示封面与任务状态，再按任务阶段提供取消、获取文件、开始分析、取消分析或重新分析。

进度值使用文本与 Radix Progress 同时表达，并通过节流的 `aria-live="polite"` 发布关键阶段变化。AI 分析成功后展示摘要、关键观点、章节和可键盘浏览的思维导图；下载失败不伪装为空状态，AI 失败不改变下载成功表达。

### 登录与注册

使用居中、窄列、无外层卡片的表单。登录突出邮箱、密码和单一蓝色主按钮；注册增加用户名与密码确认。错误出现在对应字段附近并在提交失败时聚焦摘要。登录态用户访问认证页时返回安全的站内目标。

### 个人资料与用户管理

个人资料以单列设置表单展示可编辑用户名，以及只读邮箱和角色；保存后导航名称同步更新。用户管理桌面端为轻量表格与筛选条，编辑角色和状态使用 Radix Dialog。管理员不能修改自己的角色或启用状态，禁用原因必须可感知。

390px 下用户管理转为摘要行/列表，详情和编辑进入适配视口的 Dialog；禁止依赖横向滚动查看邮箱、角色或操作。

### 404

静态 404 使用品牌、短句和返回首页操作，不显示调试信息。FastAPI 对未知 UI 地址返回该页面和真实 404 状态。

## 响应式规范

390×844 是强制验收视口，不是事后缩放桌面布局。

- 页面不得出现横向滚动，任何固定宽度必须受 `max-width: 100%` 约束。
- 首页 URL 输入与解析按钮改为上下排列，按钮满宽；结果改为单列，先展示格式与下载动作，再展示媒体摘要。
- 封面保持 16:9，不拉伸、不裁掉关键信息；长标题最多按上下文截断并保留完整可访问名称。
- 表格、筛选条、表单按钮和 Dialog 采用移动布局；主操作满宽，操作之间至少 8px。
- 导航、单选行、菜单、分页和关闭按钮的触控目标至少 44×44px。
- 软键盘出现时表单仍能滚动到错误字段和提交按钮，不使用遮挡内容的固定底栏。

## 可访问性规范

目标为 WCAG 2.2 AA：

- 使用 `header/nav/main/footer`、唯一 `h1`、顺序标题、真实 `form/label/button/table`；不得用可点击 `div` 代替控件。
- 正文对比度至少 4.5:1，大字至少 3:1，控件边界和焦点指示至少 3:1。
- 所有交互可仅用键盘完成；焦点顺序与视觉顺序一致。焦点环至少 2px，并与背景留出 2px 偏移。
- Radix Dialog、Select、Dropdown Menu 等保留其焦点管理、Escape 关闭和语义属性，不覆盖为不可访问的自定义行为。
- 异步加载、错误、下载/分析阶段变化使用适当的 `aria-live`，但不得在每次轮询时重复播报。
- 图片提供符合上下文的替代文本；标题已经完整描述内容时，装饰封面可使用空替代文本以避免重复。
- 图标不能单独承担名称；表单错误通过文本与 `aria-describedby` 关联；必填、禁用和当前状态不得只靠颜色。
- 支持浏览器缩放至 200%，并在 `prefers-reduced-motion` 下取消非必要动画。

## 设计 QA 门禁

首页在 1487×1058 视口、解析成功状态下与方案 2 原图进行同状态对比；必须把参考图和实现截图放入同一比较输入，而不是分别凭记忆判断。重点核对导航密度、首屏纵向位置、输入尺寸、三步节奏、两栏比例、封面裁切、格式行、字体重量、圆角与留白。

全部路由还需在桌面视口和 390×844 下检查真实数据、加载、空、错误、打开菜单/弹窗等关键状态。P0/P1/P2 差异修复后重新截图比较，根目录 `design-qa.md` 只有在写明 `final result: passed` 后才可交付；剩余 P3 只能作为后续微调记录。

设计 QA 不能替代功能、静态导出、OpenAPI 漂移、axe 与键盘验收。
