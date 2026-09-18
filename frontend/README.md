# Frontend

帧取 Web 前端，属于 video-server。使用 Next.js App Router、React、TypeScript strict、Tailwind CSS、官方 shadcn/ui（radix-nova / neutral / Phosphor）。工程遵循 create-next-app 的 src 目录与 @/* 别名；视觉标准见 [design.md](../design.md)。

## 开发与验证

Node.js 24，pnpm 版本以 package.json 的 packageManager 为准。只维护 pnpm-lock.yaml。

```bash
pnpm install --frozen-lockfile
pnpm dev
pnpm format:check
pnpm lint
pnpm test
pnpm build
```

生产输出为 Next.js standalone。前端监听 8101，FastAPI 监听 8111；src/proxy.ts 按运行时 BACKEND_ORIGIN 将 /api/*、/health/* 转发到后端，上传使用流式代理。生产入口须将 /api/ws/tasks 的 WebSocket Upgrade 转发到 FastAPI。基础设施复用当前宿主机服务，部署命令见根 README。

## 目录

```text
src/
├── app/          路由、布局、元数据与全局主题
├── api/          Umi OpenAPI 生成的请求函数与 API 类型
├── components/   按业务组织的组件；ui/ 保存官方 shadcn 源码
├── hooks/        状态、查询与任务流程
├── lib/          request.ts Axios 封装、错误处理与浏览器基础能力
├── services/     上传、取消清理和媒体处理等多步业务编排
├── types/        前端业务类型；接口类型复用 API
└── utils/        格式化、校验与幂等键
```

不维护旧 src/services/video 或手写的 API 转发层。

## 自动生成接口

后端 FastAPI 从路由装饰器、类型注解、Pydantic 请求/响应模型自动产生 /openapi.json，/docs 展示 Swagger UI。接口定义只在后端代码维护，不手写 Swagger 文件。

```bash
pnpm openapi
```

@umijs/openapi 读取 openapi2ts.config.ts，默认从 http://127.0.0.1:8111/openapi.json 生成 src/api/。也可设置 OPENAPI_SCHEMA_URL 指向其他后端或从后端自动导出的临时 schema；不提交临时文档或本地地址。运行的是官方 CLI 的 Node 入口，避免已发布 bin 的 CRLF shebang 在 Unix 下执行失败，不增加包装脚本。

- 所有 REST 请求函数与接口类型都由生成器维护，禁止手写或修改 src/api 文件。
- 页面、Hooks 与业务编排直接导入生成函数。
- 所有生成函数调用 src/lib/request.ts 中的 Axios request，统一处理超时、Cookie、认证恢复和 RFC Problem Details。
- 路径参数按生成签名传入对象；幂等键、取消信号、上传回调和二进制 responseType 通过 RequestOptions 传递。
- 后端二进制响应必须声明 string/binary，生成器通过官方 customType hook 映射为 Blob；不手工补类型。
- Access/Refresh JWT 仅存于 HttpOnly Cookie；认证恢复最多重试一次，并发失败共享刷新请求。
- 接口变化时先更新后端注解并重启后端，再执行生成、类型检查和相关测试，提交生成差异。

## 官方组件

```bash
pnpm dlx shadcn@latest info --json
pnpm dlx shadcn@latest docs input select
pnpm dlx shadcn@latest add input --dry-run
pnpm dlx shadcn@latest add input --diff input.tsx
```

保留官方组件 API、焦点、错误与浮层行为。页面使用留白组织无边框布局，不强制覆盖基础控件边界。主题采用官方 neutral tokens 和圆角比例；cn 使用官方组件依赖的 cn 包。Progress 向 Radix 传递 value，确保辅助技术可读进度；该修正由测试保护。

Biome 对官方 ui 源码中有明确用途的角色、事件、数组 key 与图表 CSS 注入使用目录级规则豁免；业务代码继续执行完整规则。pnpm-workspace.yaml 明确拒绝不需要的 es5-ext 安装脚本。

## 验证边界

Vitest 覆盖认证恢复、生成请求、上传、下载、分析和页面交互。浏览器额外检查桌面/390px、明暗主题、导航、焦点和溢出。生成成功、单元测试或构建成功均不等于 YouTube、抖音等平台的真实解析/下载验收。
