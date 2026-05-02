# 万能视频下载器

这是一个合规、安全、可自部署的视频下载与内容整理工具。当前阶段为 M1 后端骨架，实现 FastAPI API、RQ Worker、PostgreSQL、Redis、MinIO / S3 私有对象存储和 yt-dlp 下载内核适配。

## 一键启动

本项目区分本地开发和生产部署两种启动方式：

- 本地开发：默认只启动本项目的 API 和 Web，不启动 Redis、PostgreSQL、MinIO，也不默认启动依赖 Redis 的 Worker。
- 生产部署：通过 Docker Compose 同时启动 Web、API、Worker、PostgreSQL、Redis 和 MinIO。

本地一键启动：

```bash
./scripts/start.sh local
```

本地一键启动不会安装或启动 Redis、PostgreSQL、MinIO。默认只启动 API 和 Web；如果需要本地验收队列下载链路，并且你已经有可用 Redis，可以启用 Worker：

```bash
START_WORKER=true ./scripts/start.sh local
```

生产一键启动：

```bash
cp .env.production.example .env.production
# 修改 .env.production 中所有 CHANGE_ME 和域名配置
./scripts/start.sh prod
```

本地默认地址：

```text
前端：http://127.0.0.1:3000
API：http://127.0.0.1:8000
```

生产 Compose 默认地址：

```text
前端：http://localhost:3000
API：http://localhost:8000
MinIO 控制台：http://localhost:9001
```

## 后端本地启动（分步）

本地开发不安装、不启动 Redis、PostgreSQL、MinIO / S3 这类基础设施；只读取 `.env` 里的连接地址。若需要分步排查，可以按下面命令启动。

1. 复制环境变量：

```bash
cp .env.example .env
```

2. 安装 Python 依赖：

```bash
./scripts/dev_install.sh
```

该命令默认使用当前本地 `python3` 环境。若你希望指定其他解释器，可以使用：

```bash
PYTHON_BIN=/path/to/python ./scripts/dev_install.sh
```

如果你的本地 Python 是 Homebrew 管理版本，可能会遇到 PEP 668 的 `externally-managed-environment` 保护。此时推荐使用已经准备好的虚拟环境、Conda 或 pyenv 解释器；如果你明确要安装到用户级 Python 包目录，可以自行追加 pip 参数：

```bash
PIP_INSTALL_ARGS="--user --break-system-packages" ./scripts/dev_install.sh
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

Worker 只在本地验收队列下载链路时需要启动；普通页面和 API 开发可以先不启动。

6. 运行后端测试：

```bash
./scripts/dev_test.sh
```

API 默认地址：

```text
http://127.0.0.1:8000
```

本地队列使用 `RQ + Redis`，不需要 RabbitMQ；Redis 只在启动 Worker 或验收下载队列链路时需要。

下载任务的本地目录是 `DOWNLOAD_WORK_DIR`，只作为 yt-dlp / FFmpeg 的临时工作目录；成品文件上传到 MinIO / S3 后会清理任务临时目录，下载交付只依赖私有 bucket 和短期预签名 URL。

## Docker 生产部署方案

Docker 基础文件只描述后端项目容器，不包含 Web 静态托管、Nginx、PostgreSQL、Redis 和 MinIO。线上生产部署会叠加 `infra/docker/docker-compose.prod.yml`，此时才构建 Nginx 托管的 Web 镜像并启动 PostgreSQL、Redis、MinIO。生产配置来自 `.env.production`，启动前会检查示例密钥、本地域名和缺失变量：

```bash
cp .env.production.example .env.production
./scripts/start.sh prod
```

## 前端本地启动

前端位于 `apps/web`，采用 React + Umi + Ant Design Pro，默认连接 `http://127.0.0.1:8000` 后端 API。

```bash
cd apps/web
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:3000
```

如需指定后端地址：

```bash
UMI_APP_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 重要边界

- 仅用于用户拥有版权、已获授权、公共领域、开放授权或平台明确允许保存的内容。
- M1 不支持 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过和平台专用解析。
- 下载文件默认保留 24 小时，下载链接默认 15 分钟过期。
