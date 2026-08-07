# Frontend

本目录是基于 Ant Design Pro 官方技术栈的前端应用：React、Ant Design、Pro Components 与 Umi Max。路由、ProLayout、开发代理、请求和 OpenAPI 生成都由 Umi Max 配置管理，不再维护 Vite 入口、自定义路由器或手写基础布局。

本地与镜像构建统一使用 Node.js 24 LTS（`>=24.15.0 <25`）和 npm 11.19；`package.json` 的 `engines` 与 `packageManager` 是版本事实来源。

## 本地开发

先在仓库的 `backend/` 目录启动 API：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8101 --reload
```

然后在本目录执行：

```bash
npm ci
npm run dev
```

开发页面由 Umi Max 启动，`/api/` 与 `/health/` 会代理到 `http://127.0.0.1:8101`。

## 目录

```text
frontend/
├── config/
│   ├── config.ts              Umi Max 插件、主题、请求与构建配置
│   ├── defaultSettings.ts     ProLayout 默认设置
│   ├── proxy.ts               本地同源代理
│   └── routes.ts              页面与菜单路由
├── src/
│   ├── app.tsx                Umi 运行时布局与请求配置
│   ├── requestErrorConfig.ts  API 错误归一化
│   ├── global.css             全局样式
│   ├── components/            跨页面复用的展示组件
│   ├── hooks/                 可复用的页面状态逻辑
│   ├── pages/                 Umi 路由页面
│   ├── services/
│   │   ├── video/             OpenAPI 自动生成代码
│   │   ├── analysis.ts        分析业务请求入口
│   │   └── download.ts        下载业务请求入口
│   ├── types/                 前端业务类型别名
│   └── utils/                 无 UI 的通用函数
└── tests/                     Vitest 测试
```

项目不使用 `features/` 切片。页面放在 `pages/`，跨页面组件放在 `components/`，请求放在 `services/`；页面私有组件可以放在对应页面的 `components/` 子目录。

## OpenAPI 客户端

FastAPI 的 OpenAPI 文档是接口类型的唯一来源。先启动 FastAPI，再执行 Umi Max 官方生成命令：

```bash
npm run openapi
```

命令默认读取 `http://127.0.0.1:8101/openapi.json`。如需使用 CI 或远端契约，可设置 `OPENAPI_SCHEMA_URL` 后再运行命令。开发服务器还会提供 `/umi/plugin/openapi`，用于预览插件读取到的 Swagger 文档。

生成结果位于 `src/services/video/`，由 `@umijs/max-plugin-openapi` 的 `max openapi` 命令维护，不要手工修改。生成器按 OpenAPI tag 分文件，并使用后端声明的 `operationId` 作为函数名；页面和 Hooks 只调用 `src/services/analysis.ts` 或 `src/services/download.ts`，避免生成代码细节扩散到 UI。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动 Umi Max 开发服务器 |
| `npm run openapi` | 从 FastAPI 文档重新生成接口代码 |
| `npm run lint` | 运行 Biome lint 与 TypeScript 检查 |
| `npm run format:check` | 检查格式 |
| `npm test` | 运行 Vitest |
| `npm run build` | 构建生产静态文件到 `dist/` |
| `npm run preview` | 本地预览生产构建 |

生产环境不运行独立前端容器。根 Dockerfile 构建 `dist/` 后，由 FastAPI 同源提供页面与 API。
