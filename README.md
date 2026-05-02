# 万能视频下载器

这是一个合规、安全、可自部署的视频下载与内容整理工具。当前阶段为 M1 后端骨架，实现 FastAPI API、RQ Worker、PostgreSQL、Redis、MinIO / S3 私有对象存储和 yt-dlp 下载内核适配。

## 后端本地启动（推荐）

本地开发默认复用你机器上已有的 Python、PostgreSQL、Redis 和 MinIO / S3 服务，不强制 Docker。

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 安装 Python 依赖：

```bash
./scripts/dev_install.sh
```

3. 确认本地服务地址：

```bash
./scripts/check_local_services.sh
```

4. 启动 API：

```bash
./scripts/dev_api.sh
```

5. 启动 Worker：

```bash
./scripts/dev_worker.sh
```

API 默认地址：

```text
http://127.0.0.1:8000
```

本地队列使用 `RQ + Redis`，不需要 RabbitMQ。

## Docker 部署方案

Docker 主要用于上线部署或需要完整隔离环境时使用。默认配置来自 `.env.docker.example`：

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

## 重要边界

- 仅用于用户拥有版权、已获授权、公共领域、开放授权或平台明确允许保存的内容。
- M1 不支持 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过和平台专用解析。
- 下载文件默认保留 24 小时，下载链接默认 15 分钟过期。
