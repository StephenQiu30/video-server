# Frontend

万能视频下载器的 Vite/React Web 模块。

本模块只负责浏览器 UI 和同源 `/api/*` 客户端，不保存基础设施或大模型密钥。开发时运行 `npm run dev`，Vite 固定代理到本地 `19090` 端口；生产时由统一 Dockerfile 构建，静态产物交给 FastAPI 提供，不运行独立 Nginx 容器。
