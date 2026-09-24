# Frontend 协作规范

本目录属于 video-server；video-app 是独立项目。遵循根 AGENTS.md 和用户最新要求。

## 技术与目录

- 官方 Next.js App Router、React、TypeScript strict、Tailwind CSS、shadcn/ui、Radix 与 Phosphor。工程参数由 package.json、tsconfig.json、components.json 管理；当前组件配置不另定视觉标准。
- 使用 pnpm 和唯一 pnpm-lock.yaml；不引入 npm/yarn 锁文件或额外生成包装脚本。
- src/app 放路由、布局和元数据；src/components 放业务组件，ui 子目录放官方 shadcn 源码；业务专用 Hooks 与组件同目录；src/hooks 仅放跨业务共享 Hooks。
- src/api 只放 @umijs/openapi 生成的请求函数与类型，禁止手写或修改。生成配置只在 openapi2ts.config.ts。
- 后端路由注解、请求与响应模型自动生成 /openapi.json 和 Swagger UI；不手写接口文档。修改后端注解后执行 pnpm openapi，同步提交生成结果。
- src/lib/request.ts 是统一 Axios 封装，负责 Cookie、认证恢复、超时和错误。业务组件、Hooks 直接调用生成 API；src/lib/upload 保留上传、导入等多步编排，不添加转发包装层。
- Web 只用 PostgreSQL 持久化的不透明 HttpOnly Cookie；不做 JWT 刷新和业务请求自动重放，依赖故障不能清空身份。App Bearer 协议独立。登录跳转必须限制为同源路径。
- Next.js standalone 服务监听 8101，FastAPI 监听 8111；保留运行时代理和上传流式代理，业务规则由后端负责。

## 组件与验证

- 根 `design.md` 是唯一的视觉设计标准；先查官方 CLI 和文档确认组件 API、交互与可访问性，更新先预览差异；必要可访问性修复需有回归测试（Progress 需向 Radix 传 value）。
- 页面与基础控件的视觉样式以根 `design.md` 为准，同时保留组件键盘、焦点和错误语义；不追加旧版非官方属性或 variant。
- 页面或列表空状态统一使用 `@/components/layout/page-empty-notice`；页面级请求失败使用 `PageErrorNotice`，已有数据刷新或操作反馈使用 `FeedbackNotice`/Sonner message，不在业务页面复制左对齐的 Empty 结构。
- Client Component 只用于交互、状态或浏览器能力；业务图标使用 Phosphor，品牌复用 public/logo.svg。
- 桌面与 390px、明暗主题均须可用，检查可访问名称、焦点恢复、溢出和错误恢复。
- 验证命令：pnpm install --frozen-lockfile、pnpm format:check、pnpm lint、pnpm test、pnpm build。
- 接口生成：pnpm openapi；可用 OPENAPI_SCHEMA_URL 指向运行中的后端或后端自动导出的临时 schema。不得提交本地临时 schema。

## 目录维护

具体职责和放置规则统一见根 PROJECT.md“前端目录与文件规则”。不恢复 services、utils、types 聚合目录；接口类型直接使用 API.*，前端专用类型就近定义。普通文件 kebab-case，Hook 文件 use-*.ts；生成目录保持生成器命名。
