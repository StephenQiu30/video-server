# 根目录 Compose 运行手册

## 三个固定职责

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 公共服务拓扑、健康检查、依赖关系、卷和内部端口 |
| `docker-compose-env.yml` | 本地 `.env`、宿主机端口和本地运行差异 |
| `docker-compose-prod.yml` | 生产 `.env.prod`、生产镜像、容器名和对外端口 |

基础文件集中定义服务拓扑，环境文件只覆盖环境差异，不复制服务依赖和健康检查；生产文件与基础文件组合使用，不再复制整套服务。仓库不使用 `deploy/` 目录。环境变量的具体值只写在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中。

## 本地环境

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.yml -f docker-compose-env.yml config --quiet
docker compose --env-file .env -f docker-compose.yml -f docker-compose-env.yml up -d --build
```

基础配置与环境配置合并后启动完整本地环境。入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。

所有服务都显式声明 `container_name`，容器名稳定为 `video-server-local-api`、`video-server-local-postgres` 等，不会出现 `xxx-1` 副本后缀。环境配置读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 生产环境

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

生产文件只提供生产环境差异；生产运行前必须替换 `.env.prod` 中的占位值。

## 网络边界

- 服务使用 Compose 默认网络互联，不额外维护命名网络。
- Media Runner 通过 egress proxy 访问外部媒体地址；proxy 不暴露宿主机端口，并继续拒绝私网、localhost 和字面量 IP 目的地址。
- API、Worker 与 Runner 使用 Compose DNS 互联，不通过宿主机端口绕行。

## 数据和停止

- 本地和生产组合分别使用独立的 Compose 项目名和作用域卷，不共享数据卷。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 常规停止使用与启动相同的文件组合执行 `docker compose ... down`；不得在未确认备份时添加 `--volumes`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:8101/health/live
curl --fail http://localhost:8101/health/ready
docker compose --env-file .env -f docker-compose.yml -f docker-compose-env.yml ps
```

若下载解析失败，先区分 URL/格式业务错误、Runner 健康、egress ACL、队列积压和对象存储，不要通过开放私网、上传 Cookie 或透传 yt-dlp 参数绕过控制。
