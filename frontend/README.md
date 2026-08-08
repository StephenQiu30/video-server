# Frontend

本目录是视频下载器的 Next.js App Router 前端，使用 React、Ant Design（`antd`）与 Ant Design Pro Components（`@ant-design/pro-components`）搭建，采用 Ant Design 主题色（`#1677FF`）与自备品牌 Logo。页面以静态导出形式构建，生产环境继续由 FastAPI 同源提供页面、`/api/*` 与 `/health/*`。

本地与镜像构建统一使用 Node.js 24 LTS（`>=24.15.0 <25`）和 npm 11.19；`package.json` 的 `engines` 与 `packageManager` 是版本事实来源。

## 本地开发

先启动后端 API：

```bash
cd ../backend
uv sync --frozen --dev
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8101 --reload
```

然后启动前端：

```bash
cd ../frontend
npm ci
npm run dev
```

页面位于 <http://localhost:3000>。Next.js 开发服务器将 `/api/*` 和 `/health/*` 代理到 `http://127.0.0.1:8101`；生产构建使用同源相对路径，不需要额外浏览器环境变量。

## 目录

```text
frontend/
├── src/app/                 App Router 页面、布局和 Tailwind 主题
├── src/components/          下载、历史、分析等业务组件
│   └── ui/                  shadcn/ui 组件源码（Radix UI primitives）
├── src/hooks/               轮询与页面状态流程
├── src/lib/                 Axios 请求封装、工具和设计预览数据
├── src/services/            下载、分析和系统请求入口
│   └── video/               Umi OpenAPI 自动生成接口与类型
├── src/types/               稳定业务类型别名
├── src/utils/               格式化、校验与幂等键
└── tests/                   Vitest 测试
```

页面组件优先组合 shadcn/ui，不直接复制第三方组件库运行时。应用使用统一的 Radix UI 包、Phosphor 图标与 Tailwind 主题 token；不再依赖 Umi Max、Ant Design 或 Pro Components。

## OpenAPI 接口生成

启动 FastAPI 后执行：

```bash
npm run openapi
```

命令按照 `openapi2ts.config.ts` 读取 `http://127.0.0.1:8101/openapi.json`，使用独立的 `@umijs/openapi` 生成 `src/services/video/` 中的接口函数和 `API` 类型。Next.js 不依赖 Umi 运行时；生成函数通过配置的 `requestImportStatement` 统一调用 `src/lib/request.ts` 中的 Axios 实例。可通过 `OPENAPI_SCHEMA_URL` 临时覆盖契约地址。

`src/services/video/` 是生成目录，禁止手工修改。业务页面只调用 `src/services/download.ts`、`analysis.ts` 或 `system.ts`，由这些稳定入口补充幂等键等业务选项。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 使用 Next.js 默认的 3000 端口启动开发服务器 |
| `npm run openapi` | 从 FastAPI 重新生成接口类型 |
| `npm run lint` | 运行 Biome lint 与 TypeScript 检查 |
| `npm run format:check` | 检查格式 |
| `npm test` | 运行 Vitest |
| `npm run build` | 静态构建到 `out/` |

生产环境不运行独立前端容器。根 Dockerfile 将 `out/` 复制为统一镜像内的 `/app/frontend/dist`，再由 FastAPI 提供。
