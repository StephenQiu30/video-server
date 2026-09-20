# YouTube 受控会话运行手册

> 浏览器来源只由当前宿主的本机 Agent 按需读取。标准生产 Compose 使用 YouTube 专用加密队列，不挂载浏览器目录或 Cookie 文件；重启与换机步骤见[个人部署手册](008-个人部署重启与换机手册.md)。

YouTube 使用统一多平台会话架构，安装、启动、撤销和故障处理见 `docs/operations/003-多平台受控会话运行手册.md`。本页只记录 YouTube 特有约束。

## 1. 访问上下文

- Provider Profile：`youtube`
- 会话版本：`browser`
- 会话来源：生产 Runner 每次操作通过 `/run/provider-cookie-agent` 请求一次性加密租约；macOS 宿主 Agent 只读取 YouTube 专用浏览器目录
- 隔离服务：`youtube-operator-runner`
- Chrome 域：`youtube.com`、`youtube-nocookie.com`
- Player 客户端：`mweb`
- POT Provider：固定 OCI digest 的 bgutil sidecar

生产请求不会先尝试匿名再切换账号。启用 `youtube-operator-runner` 并显式设置 `RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}` 后，YouTube inspect 直接进入该 Runner；download 必须使用 inspect 冻结的同一上下文。会话失败返回稳定错误，不能改走匿名或其他账号。

## 2. 生产来源维护

在本机专用浏览器目录完成 YouTube 第一方登录后，从 `backend/` 执行一次授权和 Agent 安装：

```bash
cd backend
uv run python -m app.workers.runner.provider_cookie_agent authorize --provider youtube
uv run python -m app.workers.runner.provider_cookie_agent install \
  --browser-root "$HOME/Library/Application Support/FrameFetch/provider-browser-sessions"
uv run python -m app.workers.runner.provider_cookie_agent doctor --provider youtube
```

本机 Agent 不在项目目录写 Cookie 文件：它按请求从 YouTube 专用浏览器目录读取最小 allowlist，使用临时公钥封装一次性租约，并在队列响应后清理请求和响应。容器只看到加密队列和 `/run/provider-session` 内的操作临时 jar。

Agent 不读取普通 Chrome Profile，不访问其他平台 Cookie，也不进入 API、下载请求或 Docker。它只在 Runner 请求时打开对应的专用浏览器目录并发布一次性加密租约。机器重启后 LaunchAgent 会按队列按需唤醒；普通项目、Docker 或 Runner 重启不会删除专用目录，也不要求再次导出文件。平台撤销授权或新宿主触发新的平台验证时，才需要重新完成第一方登录。

开发和生产均需启用 `youtube-operator` Profile，不会因配置了端点自动启动。无 macOS 本机 Agent 的 Linux 或无人桌面部署只启用匿名路线；如果明确需要受控 YouTube，应使用受批准的自定义文件来源配置，不把标准 Compose 的 Agent 队列伪装成可用。

### macOS 生产部署

文件来源仍可作为高级迁移/灾备通道。用户明确授权后，可以从当前 Chrome 显式采集 YouTube 的单平台文件，但标准生产 Compose 不读取它。在私有 `.env.prod` 设置：

```dotenv
COMPOSE_FILE=docker-compose-prod.yml
COMPOSE_PROFILES=youtube-operator
RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}
```

已有其他 profile 或默认策略时合并保留，不能覆盖。首次授权并安装 Agent 后执行：

```bash
docker compose --env-file .env.prod -f docker-compose-prod.yml \
  up -d --build --force-recreate --wait --wait-timeout 300
```

生产 Runner 只挂载 YouTube 的加密队列，不持有 Chrome 数据库、密码或其他网站会话。

账号退出、平台撤销或新机授权仍需在第一方页面重新验证；Agent 不会恢复已撤销授权。此时保留准确的 `provider_session_expired`，完成授权后重新执行真实 metadata/media，不重启全部服务。

## 3. POT 与出口

POT 只解决 Player/GVS 请求证明，不能修复登录过期、账号权益或被挑战的出口。`youtube-pot-provider` 必须保持固定镜像 digest，并与 YouTube Runner 使用同一受管出口。不得使用公共代理、WARP/Tor、cobalt 或 Invidious 作为可用性基础。

生产验证至少包括：

```bash
docker compose --env-file .env.prod -f docker-compose-prod.yml \
  exec -T youtube-operator-runner yt-dlp --version
docker compose --env-file .env.prod -f docker-compose-prod.yml \
  exec -T youtube-pot-provider node -e \
  "fetch('http://127.0.0.1:4416/ping').then(r=>r.json()).then(v=>{if(v.version!=='1.3.2')process.exit(1)})"
cd backend
uv run python -m app.workers.canary.fixed_matrix --provider youtube
```

只有 metadata、完整媒体、ffprobe、SHA-256 和浏览器下载全部成功，且 private、会员、付费与 DRM 反例全部关闭失败时，才可认为当前 YouTube 上下文可用。
