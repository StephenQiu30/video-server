# 根目录 Compose 运行手册

## 运行模型

业务拓扑只有一个运行入口：根目录 `docker-compose.yml`。本地可继续复用由 Homebrew
管理的 PostgreSQL、RabbitMQ、Redis 和 MinIO，但前端、API、Worker、Runner 与
Operator 必须处于同一 Compose 网络；不提供宿主机业务进程与容器 Operator 混合运行入口：

| 文件 | 用途 | 是否启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| --- | --- | --- |
| docker-compose-env.yml | 本项目专用基础环境 | 是，仅启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| docker-compose.yml | 本机/共享环境运行，只启动业务容器 | 否，复用宿主机已有服务 |
| docker-compose-prod.yml | 独立的生产业务容器运行配置，与默认拓扑保持一致 | 否，复用生产宿主机服务 |

默认业务拓扑包含 API、Outbox、下载 Worker、导入 Worker、报告 Worker、Provider Canary、Media Runner 和受控出口代理。YouTube Operator 与其他 Provider Operator 只通过对应 profile 显式启用。

Compose 文件不再通过 YAML Anchor 隐式继承服务配置；每个服务直接声明自己的角色、连接地址、挂载、网络和启动命令。

## Docker 文件使用规范

- `docker-compose-env.yml` 只部署本项目专用的 PostgreSQL、RabbitMQ、Valkey 和 MinIO，并负责一次性初始化；`docker-compose.yml` 只部署业务容器；`docker-compose-prod.yml` 只提供生产业务容器差异。
- 业务 Compose 通过 `POSTGRES_HOST/PORT`、`RABBITMQ_HOST/PORT`、`VALKEY_HOST/PORT` 和 `MINIO_HOST/PORT` 连接基础服务。启动 `docker-compose-env.yml` 时使用服务名和容器端口；复用已有基础服务时改为宿主机可达地址和已发布端口。
- `HOST_*_PORT` 仅用于环境 Compose 向宿主机发布端口，不是业务容器的连接端口。不要把两类端口混用。
- MinIO 只配置一组 `MINIO_ACCESS_KEY` 与 `MINIO_SECRET_KEY`，所有业务进程共用；不要按 API、导入、下载、报告或分析进程复制密钥变量。
- 仓库环境 Compose 将 `MINIO_CORS_ALLOWED_ORIGINS` 直接映射为 MinIO 实例级 `MINIO_API_CORS_ALLOW_ORIGIN`。固定 digest 的一次性 `minio-config-check` 会先拒绝空值、通配符、路径、userinfo、非法主机、越界端口和非 HTTP(S) 值；只有校验成功后，保留官方 entrypoint 的 MinIO 才会启动。列表中的每一项必须是完整的 `scheme://host[:port]` exact origin；修改后重新执行环境 Compose 的 `up -d` 以重建 MinIO 容器，不能使用 `restart`。
- CI、开发和本机验收必须复用上述正式 Compose 文件，不新增仅供某个环境的覆盖文件。

## 宿主机基础设施

不启动 docker-compose-env.yml 时，使用 docker-compose.yml 或 docker-compose-prod.yml 前，宿主机必须已经提供：

- PostgreSQL
- RabbitMQ
- Valkey/Redis
- MinIO

容器通过 `.env` 中的连接地址访问这些服务。生产环境的连接地址和凭据只放在本地 .env.prod，不能提交到 Git。

复用外部 MinIO 时，部署者必须在该实例的启动环境中设置与 `.env` 相同的 `MINIO_API_CORS_ALLOW_ORIGIN` exact-origin 列表并重建实例；不能依赖手工 bucket CORS、`*` 或遗留实例状态。社区版 MinIO 的浏览器上传策略是实例级 API 配置，仓库不会尝试调用不受支持的 bucket CORS API。无法控制外部实例启动配置时，应关闭 `MEDIA_IMPORT_ENABLED` 与 `DOCUMENT_IMPORT_ENABLED`，而不是放宽 CORS。

本机开发同时需要从浏览器和真机 App 上传时，`MINIO_PUBLIC_ENDPOINT` 应配置为真机可访问的 HTTPS 地址，`MINIO_LOCAL_BROWSER_ENDPOINT` 配置为 `127.0.0.1:<port>`。只有来自回环页面、显式标记为本地 Web 的开发请求会使用回环签名地址；Flutter 和远程 Web 始终使用公共地址。该分流由项目配置完成，不依赖或修改操作系统代理规则。生产环境应省略 `MINIO_LOCAL_BROWSER_ENDPOINT`。

私有 Tailnet 生产部署应使用节点的 Tailscale HTTPS 名称作为 `SITE_URL`，不能使用 `http://100.x.y.z`。`SITE_URL` 只生成公开元数据与绝对链接，不会把直接访问的 `8101` 请求重定向到 Tailscale；HTTPS 和规范域名跳转如有需要，应由部署入口配置。手机和 Mac 通过 Tailnet HTTPS 使用 `Secure` 会话 Cookie，远程 Web 与移动端继续使用 `MINIO_PUBLIC_ENDPOINT` 的 HTTPS 地址；本机开发可直接使用 `http://127.0.0.1:8101`。

macOS 若启用了系统 HTTP/HTTPS/SOCKS 代理，活动网络服务的代理绕过列表必须包含 `100.64.0.0/10` 与 `*.ts.net`。否则 Safari/WebKit 会把 Tailnet TLS 请求交给公网代理，而不是经 Tailscale `utun` 接口直连，表现为证书正常但页面无法建立安全连接。该规则属于 Tailnet 路由边界，不是浏览器兼容分支；修改后应在 WebKit 网络日志中确认目标 `100.x` 地址通过 `utun` 连接。

## 本机业务拓扑

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml config --quiet
docker compose --env-file .env -f docker-compose.yml config --quiet
# 首次使用或基础依赖尚未运行时执行一次
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
~~~

最后一条 Docker Compose 命令是本机完整项目的启动与重启入口。它统一构建前端与
后端镜像、重新创建业务服务并等待健康检查。需要 Operator Runner 时，在 `.env` 的
`COMPOSE_PROFILES` 中声明与 `RUNNER_OPERATOR_BASE_URLS` 一致的 profile。项目启动
不会在项目启动或解析时启动宿主机浏览器，也不会调用 AI Worker 获取平台会话。
生产受控 Provider 不使用版本化 Cookie 文件。macOS 部署显式安装统一按需助手后，
Operator 操作才会读取 Chrome Default 的目标域最小集合；SQL 查询本身按中央 Provider
allowlist 选择，不把其他域行返回后再过滤。Runner 每次生成一次性公钥，宿主返回绑定该
请求的认证加密密文；明文只在对应 Runner 的 `/run/provider-session` tmpfs 中存在到操作
结束。单次读取有 15 秒硬超时，超时或取消会回收整个进程组；请求排空后 helper 退出，
不会留下 Chrome 后台进程、Cookie 文件或项目专用浏览器 Profile。该 helper 只是按需的
本机凭据适配器，不是平行应用启动方式；项目仍只通过上述 Docker Compose 命令运行。
不要使用不会应用代码、镜像或配置变化的
`docker compose restart`。

出口目的地址策略必须匹配 Docker 运行环境。Linux 服务器保持
`EGRESS_DESTINATION_POLICY_FILE=./backend/egress/blocked-destinations.conf`；macOS/Windows
Docker Desktop 会把公网 DNS 映射到保留的 synthetic 地址段，必须显式选择
`blocked-destinations-docker-desktop.conf`。后者仍拒绝字面量 IP URL、私网 DNS 结果和
非 Web 端口，不能在普通 Linux 服务器上作为放宽策略使用。修改后必须重建
`egress-proxy`，仅重启其他业务容器不会应用挂载变化。

访问地址：

- Web：http://localhost:8101
- API/Swagger UI：http://localhost:8111/docs
- OpenAPI：http://localhost:8111/openapi.json

如果只需要容器内的受控出口代理：

~~~bash
docker compose --env-file .env -f docker-compose.yml up -d egress-proxy
~~~

## 完整隔离环境

项目专用基础环境只需在首次使用或依赖未运行时准备一次，随后由唯一业务 Compose
入口复用：

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
~~~

代码同步与服务启动保持解耦；需要更新时先执行：

~~~bash
git pull --ff-only
~~~

随后执行上面的唯一业务 Compose 命令。YouTube、TikTok、X 完整媒体 Canary 属于
启动后的验收步骤，不与项目生命周期耦合；命令见
`docs/operations/007-固定Provider探针运行手册.md`。

项目专用环境与本机已有同端口服务不要同时运行，避免端口冲突；业务 Compose 不会自动启动基础环境。

## 生产环境

.env.prod 只允许由部署者在本机或 Secret 管理系统生成。仓库中的 .env.prod.example 只包含占位值。

~~~bash
cp .env.prod.example .env.prod
# 替换全部 replace-with-* 占位值
docker compose --env-file .env.prod -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml up -d --no-build
~~~

生产镜像必须先以 video-server:prod 的名称加载或发布。生产 Compose 不启动基础设施初始化服务，也不包含 environment profile。

生产健康检查：

~~~bash
curl --fail http://127.0.0.1:8111/health/live
curl --fail http://127.0.0.1:8111/health/ready
~~~

## AI Worker

AI Worker 继续运行在宿主机，不由 Compose 启动。Agent 必须读取与业务 Compose 相同的环境文件；本地组合使用默认 `.env`，生产组合显式传入 `.env.prod`：

~~~bash
cd backend
uv run python -m app.workers.analysis.agent_cli doctor
uv run python -m app.workers.analysis.agent_cli install
uv run python -m app.workers.analysis.agent_cli status
~~~

~~~bash
uv run python -m app.workers.analysis.agent_cli doctor --env-file ../.env.prod
uv run python -m app.workers.analysis.agent_cli install --env-file ../.env.prod
uv run python -m app.workers.analysis.agent_cli status
~~~

AI Worker 心跳是功能级状态，不是 API 全局 readiness。Worker 短暂重启时分析任务
保持 `queued`，下载、上传和历史查询继续可用；不提供分析能力的部署仍应显式设置
`ANALYSIS_ENABLED=false` 后重建 API。

## Operator Profile

macOS 生产环境先安装统一宿主会话代理：

~~~bash
cd backend
uv run python -m app.runner.provider_cookie_agent install
uv run python -m app.runner.provider_cookie_agent status
~~~

生产 Compose 固定启动九个平台隔离 Runner，不使用条件 Profile：

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml \
  up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
~~~

启用前必须按对应 Provider 运维手册完成 Cookie、权限、固定出口和授权 canary 门禁。

## 停止和数据安全

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml down
~~~

不要在未确认备份的情况下使用 --volumes。 .env、.env.prod、Cookie、Authorization、Provider key 和完整模型输出不得进入日志或 Git。
