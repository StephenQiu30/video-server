# Frontend 协作规范

本文件通过 `frontend/AGENTS.md` 符号链接作用于整个前端目录，并补充仓库根 `AGENTS.md`。冲突时遵循根规范；实现、测试和文档必须反映当前 Next.js 前端，不保留 Umi、Ant Design 或旧路由兼容层。

## 技术边界

- 使用 Next.js App Router、React、TypeScript strict、Radix UI、shadcn/ui 与 Tailwind CSS。
- 页面、布局、元数据、loading/error/not-found 边界放在 `src/app/`。
- 跨页面业务组件放在 `src/components/`；shadcn/ui 源码和 Radix 组合组件放在 `src/components/ui/`。
- 状态流程放在 `src/hooks/`，请求基础设施放在 `src/lib/`，稳定业务请求入口放在 `src/services/`。
- 不新增 `src/pages/`、`features/`、Umi/Vite 入口、平行路由器、Ant Design 运行时或第二套基础组件库。
- 单个文件超过约 200 行时按真实职责拆分，不以转发文件或空抽象规避该约束。

## 常用命令

从 `frontend/` 执行：

```bash
npm ci
npm run openapi
npm run lint
npm run format:check
npm test
npm run build
```

使用 npm 和仓库 `package-lock.json`，Node/npm 版本以 `package.json`、根 Dockerfile 和 CI 的一致配置为准。不要引入 yarn、pnpm 或第二份锁文件。

## OpenAPI 与请求

- `/openapi.json` 是前后端唯一接口契约，生成配置位于 `openapi2ts.config.ts`。
- `src/services/video/` 由独立的 `@umijs/openapi` 生成，禁止手工修改、复制类型或创建平行客户端。
- 接口变化时先更新 FastAPI schema 与稳定 `operationId`/tag，启动 API 后运行 `npm run openapi`。
- 生成函数必须通过 `src/lib/request.ts` 的同源 Axios 封装；业务组件只调用 `src/services/` 暴露的稳定入口。
- 请求层统一处理 RFC Problem Details、超时和认证恢复；页面中不得散落原始 Axios/fetch、401 刷新或错误码映射。

## 客户端鉴权

- Access JWT 与 Refresh JWT 只存在于 HttpOnly Cookie，前端不得读取、持久化或复制令牌。
- Access 失效时最多刷新并重试原请求一次；刷新失败后收敛到未登录状态，禁止无限重试。
- 登录后的返回地址必须是经过校验的同源路径，不能接受任意外部跳转。
- 客户端路由和导航可按当前用户隐藏管理员入口，但后端 403 始终是最终权限判定。
- 退出登录后清理内存中的用户态并返回登录页，不将业务数据当作会话凭据保存在浏览器。

## App Router 与静态导出

- 优先使用 Server Component；只有交互、状态或浏览器 API 需要时才添加 `'use client'`，并把客户端边界控制在最小范围。
- 动态任务路由必须为静态导出提供可构建的壳层，并在客户端读取运行时参数；不得依赖 Next.js Server、Server Action 或生产时动态渲染。
- `next.config.ts` 保持 static export，生产构建产物为 `out/`。
- 根 Dockerfile 将 `out/` 复制到 `/app/frontend/out`，由 FastAPI 同源提供页面、`/api/*` 和 `/health/*`；不要增加独立前端生产容器。
- 开发代理只服务本地联调，业务代码始终使用同源相对路径。
- 深链接刷新必须返回对应页面；未知 `/api/*` 不得回退到 HTML。

## 组件与样式

- 优先复用 `src/components/ui/` 和已有业务组件；Radix primitive 负责菜单、对话框、选择、标签页等交互语义。
- 样式只使用 Tailwind CSS 与 `src/app/globals.css` 中的语义 token，不新增 Less、CSS-in-JS 主题或 Ant Design token。
- 唯一视觉基线是用户确认的方案 3：Vercel Home 式无边框中性界面。浅色使用 `#FAFAFA` 画布、`#0A0A0A` 前景和 `#111111` 主操作；深色使用 `#0A0A0A` 画布与 `#F5F5F5` 前景。状态、表面和文字只消费 `globals.css` 的语义 token，不恢复蓝色企业后台或 Apple 蓝主操作。
- 80px Header 与常规 main/footer 复用 `.content-shell = min(calc(100% - 160px), 1376px)`，保证导航和主体对齐；根滚动容器必须保留稳定的 scrollbar gutter，Header 的异步账户区域必须使用固定宽度槽位，禁止因页面长短或认证恢复改变导航几何。认证双栏 main 是唯一例外，可使用更宽的 `.page-shell = min(calc(100% - 80px), 1456px)`，右侧表单在内部收窄到 440px，不足 `lg` 时隐藏介绍栏并水平居中。完整桌面导航从 `lg` 开始展示，其余宽度使用移动 Sheet。641–1023px 时常规内容两侧各 32px，不超过 640px 时两种网格两侧各 16px。网格只提供对齐，不得呈现为可见外框。
- 字体统一为自托管 Geist Sans/Mono 与仓库规定的中文系统回退。首页编辑式标题使用 `.editorial-title` 响应式尺度；内页使用短标题与清晰层级，不强制旧的 32px/28px 固定尺寸。页面主标题上方只有真实流程编号可以使用 `.eyebrow`，不得添加“任务记录”“账户设置”“系统管理”等装饰性重复眉题；区段标签也应克制且不与标题重复。
- Vercel 风格的无边框布局依靠留白、排版、实心中性表面和 Separator 组织内容。页面根、标题区、筛选区、列表区和表单区不使用可见 Card 外壳、装饰性 ring、重阴影或大圆角容器；输入、选择器和按钮默认无边框。焦点、错误、表格/列表分隔及 Dialog、Sheet 等覆盖层的功能边界必须保留。因语义复用 Card 时使用 `border-0`、`ring-0`、`shadow-none`，不得 Card 套 Card。
- 基础圆角只从 `--radius: 6px` 派生，不在业务组件中硬编码近似主题色、任意圆角或一次性阴影；修改 token、网格或基础控件时同步根规范、009 设计文档与必要测试。
- 基础控件的 hover、active、loading 和选中反馈不得改变外部几何尺寸或在文档流中位移；Button、Link 与 Radix Trigger 只过渡颜色、透明度及覆盖层属性，异步内容使用与最终摘要、工具条或操作同尺寸的固定槽位。Radix `asChild` 只组合语义和行为，不得借此注入让触发器位移的共享样式。
- 功能图标统一使用 `@phosphor-icons/react`；品牌标识通过 Next.js `Image` 使用 `public/logo.svg`。不使用 emoji、文本符号、手写 SVG、CSS 图形或第二套图标库代替产品图标。
- 所有已认证的非首页页面与多步骤流程都使用统一 `BackLink`：有精确站内上一条历史时执行浏览器后退，直接访问时落到稳定的层级 fallback。登录与注册不显示通用历史返回，只使用彼此的交叉链接和校验后的 `redirect`，避免过期受保护页面形成认证循环。

## 可访问性与响应式

- 使用原生语义元素和 Radix 的键盘行为；不要用带点击事件的 `div` 代替按钮、链接或表单控件。
- 控件必须有可关联标签，错误与异步状态需要可被辅助技术感知，焦点顺序和焦点环必须可见。
- 保持足够颜色对比度，不能只靠颜色表达状态，并尊重 `prefers-reduced-motion`。
- 桌面与 390px 视口都要检查页面级横向溢出、内容裁切、点击目标、表格/筛选降级和主操作可达性。

## 修改与验证

- 修改前先阅读相邻页面、组件、服务、测试和 `frontend/README.md`，优先复用现有实现。
- 不编辑生成目录、构建产物、`.next/`、`out/`、`node_modules/` 或旧 `.umi/` 缓存。
- 页面迁移必须保留当前路由、认证恢复、下载/分析状态、历史筛选、资料修改和管理员权限行为。
- 根据改动范围执行最小充分测试；前端架构或组件迁移完成后至少运行 lint、format、tests 和 production build。
- 涉及 OpenAPI 时重新生成客户端并检查差异；涉及静态交付时验证根镜像仍从 `out/` 复制到 FastAPI 的 dist 目录。
