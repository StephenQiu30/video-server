# Frontend

万能视频下载器的 Vite/React Web 模块。

本模块只负责浏览器 UI 和同源 `/api/*` 客户端，不保存基础设施或大模型密钥。开发时运行 `npm run dev`，Vite 固定代理到本地 `19090` 端口；生产时由统一 Dockerfile 构建，静态产物交给 FastAPI 提供，不运行独立 Nginx 容器。

## OpenAPI 客户端

前端使用 `@umijs/openapi` 从 FastAPI 的 Swagger/OpenAPI 文档生成请求函数与 TypeScript 类型，生成目录为 `src/generated/api`。先启动本地 API，再执行：

```bash
npm run openapi
```

默认文档地址为 `http://127.0.0.1:19090/openapi.json`。需要使用其他环境的 Swagger 文档时，可显式覆盖：

```bash
OPENAPI_SCHEMA_URL=https://api.example.com/openapi.json npm run openapi
```

`src/generated/api` 只由生成器维护；业务层通过 `features/*/api.ts` 使用生成的服务，不在生成目录中手工修改请求或类型。
