# YouTube 受控会话运行手册

> 浏览器来源只用于本机开发诊断和显式采集。生产 YouTube 使用独立只读文件；重启与换机步骤见[个人部署手册](008-个人部署重启与换机手册.md)。

YouTube 使用统一多平台会话架构，安装、启动、撤销和故障处理见 `docs/operations/003-多平台受控会话运行手册.md`。本页只记录 YouTube 特有约束。

## 1. 访问上下文

- Provider Profile：`youtube`
- 会话版本：`browser`
- 会话来源：操作开始时读取 Chrome `Default`，通过一次性加密租约交付
- 隔离服务：`youtube-operator-runner`
- Chrome 域：`youtube.com`、`youtube-nocookie.com`
- Player 客户端：`mweb`
- POT Provider：固定 OCI digest 的 bgutil sidecar

生产请求不会先尝试匿名再切换账号。启用 `youtube-operator-runner` 并显式设置 `RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}` 后，YouTube inspect 直接进入该 Runner；download 必须使用 inspect 冻结的同一上下文。会话失败返回稳定错误，不能改走匿名或其他账号。

## 2. 会话代理

在 Chrome `Default` Profile 登录 YouTube，然后安装统一代理：

```bash
cd backend
uv run python -m app.runner.provider_cookie_agent install
uv run python -m app.runner.provider_cookie_agent status
```

代理只查询 YouTube 域行并要求至少存在一个已登记的 Google 会话 Cookie。Runner 为每次操作生成一次性 X25519 密钥；宿主代理只把当前 Cookie 加密给该次请求，确认领取后删除密文。明文不进入请求队列、日志、容器环境、项目目录或宿主持久文件。

配置：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100"}
PROVIDER_COOKIE_AGENT_RUNTIME_DIR=
```

Runner 只在容器独占 tmpfs `/run/provider-session` 中为 yt-dlp 创建本次操作所需的 `0600` jar，并在操作终态删除；不能用磁盘目录替代该挂载。

开发和生产均需启用 `youtube-operator` Profile，不会因配置了端点自动启动。

### macOS 生产部署

用户明确授权后，可以从当前 Chrome 显式采集 YouTube 的单平台文件。采集仅在来源安装或失效维护时执行，生产 Runner 不读取 Chrome。在私有 `.env.prod` 设置：

```dotenv
COMPOSE_FILE=docker-compose-prod.yml
COMPOSE_PROFILES=youtube-operator
RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}
```

已有其他 profile 或默认策略时合并保留，不能覆盖。使用 `provider_session_setup capture-chrome` 采集并验收 `.provider-sessions/youtube/cookies.txt`；日常启动和容器重建统一使用 `docker compose --env-file .env.prod up -d --no-build`。生产只有一个 Compose 文件，容器只读挂载该平台文件，不持有 Chrome 数据库、密码或其他网站会话。

来源失效时只更新 YouTube 文件并重新验证，不在用户点击下载时采集，不处理验证码。账号变更及新机授权需重新验证，不能视作自动恢复已撤销授权。

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
