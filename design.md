# 前端实现规范

## 当前决策

以官方 Next.js 与 shadcn 实现为基线。旧项目设计和旧方案图不决定基础组件代码；页面保持无边框内容布局，输入、选择、按钮和浮层使用官方控件。

## 工程

- Next.js App Router、React、TypeScript strict、Tailwind CSS，遵循 create-next-app 的 src 目录和 @/* 别名。
- pnpm 版本固定在 package.json；唯一锁文件为 pnpm-lock.yaml。本地、CI 与 Docker 使用同一版本。
- shadcn CLI 管理 radix-nova / neutral / Phosphor 组件，components.json 记录配置。cn 使用官方组件引入的 cn 包。
- 不引入平行路由、主题引擎、重复基础控件或无用途兼容层。

## 接口

FastAPI 路由注解与 Pydantic 模型自动产生 /openapi.json；Swagger UI 展示同一契约。@umijs/openapi 将请求与类型直接生成至 frontend/src/api/，统一导入 src/lib/request.ts 的 Axios 封装。

修改接口只修改后端注解和模型，然后运行 pnpm openapi；禁止手写 Swagger、API 请求函数和重复类型。二进制响应由后端声明 string/binary，生成配置映射为 Blob。业务编排留在所属业务目录或共享的 lib/upload，不保留仅转发参数的包装层。

## 页面与组件

- 页面层以内容、排版和留白分组，复用 BasicLayout 的 Header、main 与 Footer。
- 基础控件保持官方 props、variant、边框、焦点、错误和浮层行为；不用无边框要求覆盖官方基础组件。
- 采用官方 neutral 明暗 token 与圆角比例；业务状态可增加有明确用途的语义 token。
- 使用官方 Radix 交互和 Phosphor 图标，保留键盘操作、表单标签与异步反馈。Progress 补充向 Radix 根节点传递 value，以正确公布进度。
- 桌面与 390px 移动视口检查内容溢出、核心操作、导航与覆盖层；尊重 reduced motion。

## 维护与验收

使用 pnpm dlx shadcn@latest info、docs 和 add --dry-run/--diff 检查官方配置和变化。更新组件后验证真实业务流程，生成 API 后运行类型检查和请求层测试。

验收包含 format、lint、Vitest、production build 与浏览器检查。实际结果记录在 design-qa.md；不能用旧截图或单元测试代替当前浏览器证据。

## 官方依据

- [Next.js 安装](https://nextjs.org/docs/app/getting-started/installation)
- [create-next-app](https://nextjs.org/docs/app/api-reference/cli/create-next-app)
- [shadcn Next.js](https://ui.shadcn.com/docs/installation/next)
- [shadcn 主题](https://ui.shadcn.com/docs/theming)
- [pnpm CI](https://pnpm.io/continuous-integration)
