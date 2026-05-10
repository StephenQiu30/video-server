# 万能视频下载器

这是一个合规、安全、可自部署的视频下载与内容整理工具。当前阶段为 M1 单用户本地 MVP，实现 FastAPI API、RQ Worker、PostgreSQL、Redis、MinIO / S3 私有对象存储和 yt-dlp 下载内核适配，优先跑通解析、任务、下载、存储和短期下载链接闭环。

## 一键启动

本项目通过 Docker Compose 实现开发环境和生产环境的快速启动：

- **应用开发环境**：启动所有项目服务（Web, API, Worker），并连接宿主机已有的数据库等环境（Homebrew 安装）。
  ```bash
  docker compose up -d
  ```
- **全量独立堆栈**：一键启动所有服务及其配套的基础设施镜像（PostgreSQL, Redis, MinIO）。
  ```bash
  docker compose -f docker-compose.prod.yml up -d
  ```

默认服务地址：
- 前端：`http://localhost:3000`
- API：`http://localhost:8000`
- MinIO 控制台：`http://localhost:9001`

## 本地开发指南

1. **环境配置**：
   复制并填写根目录的 `.env` 文件。
   ```bash
   cp .env.example .env
   ```

2. **启动基础依赖**：
   ```bash
   docker compose up -d
   ```

3. **运行后端**：
   ```bash
   cd apps/api
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

4. **运行 Worker**：
   ```bash
   cd apps/worker
   pip install -r requirements.txt
   python -m worker.main
   ```

5. **运行前端**：
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

## Docker 部署方案

本项目采用统一的根目录 `Dockerfile` 进行多阶段构建。

- **构建并启动全量堆栈**：
  ```bash
  docker compose -f docker-compose.prod.yml up -d --build
  ```

- **停止并清理**：
  ```bash
  docker compose -f docker-compose.prod.yml down
  ```

所有容器均使用 `stephen-video-` 前缀命名，方便管理。

## 前端本地启动

前端位于 `apps/web`，采用 React + Vite + Shadcn UI + GSAP，默认连接 `http://127.0.0.1:8000` 后端 API。

```bash
cd apps/web
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:3000
```

如需指定后端地址，请修改 `.env` 或在启动时指定环境变量：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 重要边界

- 仅用于用户拥有版权、已获授权、公共领域、开放授权或平台明确允许保存的内容。
- M1 不支持 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过和平台专用解析。
- 下载文件默认保留 24 小时，下载链接默认 15 分钟过期。
