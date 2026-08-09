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
- 视觉基线是简洁的蓝白界面：浅色表面、克制的层级、蓝色主操作，不使用大面积黑色主题。
- 所有路由的页面级 Header、main 与 footer 必须复用同一最大 1200px 外框：桌面宽度为 `min(calc(100% - 48px), 1200px)`，390px 视口宽度为 `min(calc(100% - 32px), 1200px)`。路由组件不得另设 1440px 或其他页面级最大宽度；认证表单、资料表单和说明文字可以在该外框内二次收窄，但不能改变页面根容器或页面标题的对齐线。
- 除首页 Hero 外，所有内页标题统一为桌面 32px/1.2、390px 28px/1.2，并使用一致的标题、说明和可选主操作结构。页面或区块标题上方不得添加装饰性蓝色 eyebrow/kicker、全大写英文标签、等宽体分类词或与标题重复的“任务记录”“账户设置”“系统管理”等说明。
- Apple 蓝只用于主操作、链接、焦点、选中/当前步骤及确有语义的状态，不用于装饰性信息或视觉层级标记；被删除的重复眉题不以灰色文案替代。
- Vercel 风格的无边框布局依靠留白、排版、表面色和 Separator 组织内容。页面根、标题区、筛选区、列表区和表单区默认不使用装饰性 Card 外框、ring、阴影或大边框；输入/选择器、表格与列表分隔、焦点、错误、Dialog、Sheet 等功能边界仍须清晰可见。因语义复用 Card 时使用 `border-0`、`ring-0`、`shadow-none`，不得 Card 套 Card。
- 图标使用项目选定的图标库，不使用 emoji、文本符号、手写 SVG 或 CSS 图形代替产品图标。
- 不在页面中硬编码近似主题色、任意圆角或一次性阴影；新增视觉值先落入语义 token。

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
