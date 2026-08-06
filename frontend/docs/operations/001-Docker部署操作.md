# Docker 部署操作

Web 镜像固定使用 Ant Design Pro/Umi 的 `npm run build` 产物，并由 Nginx 提供 SPA 静态资源和 `/api/` 反向代理。浏览器只访问 Web 同源地址，不在页面中暴露基础设施配置。

## 默认环境

先按 `video-server` 的 Docker 操作启动服务端，再执行：

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

默认访问地址为 `http://localhost:8000`。`VIDEO_API_UPSTREAM` 只供 Nginx 容器使用，默认通过 `host.docker.internal:19090` 访问宿主机发布的 API；`VIDEO_API_BASE_URL` 保持为空，确保浏览器走同源 `/api/`。

## prod 环境

```powershell
Copy-Item .env.prod.example .env.prod
# 替换镜像和内部 API 地址
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml ps
```

生产入口的 TLS 和域名由部署平台负责。`VIDEO_API_UPSTREAM` 必须是容器可达的私网 `host:port`，不能带路径；服务端 `.env.prod` 的 `WEB_ORIGIN` 必须与用户实际访问的 Web Origin 完全一致。

## 健康检查与回滚

- Web 容器健康检查：`GET /healthz`。
- API readiness 由服务端 `GET /health/ready` 独立判断，Web 不伪造后端健康状态。
- 回滚时将 `.env.prod` 的 `VIDEO_WEB_IMAGE` 改为已验证的旧版本标签，再重复 prod 启动命令。
- 停止服务使用 `docker compose down`；Web 无业务数据卷。
