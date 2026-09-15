# YouTube 受控会话运行手册

> 浏览器来源只由本机宿主维护进程读取。生产 YouTube 使用独立只读文件；重启与换机步骤见[个人部署手册](008-个人部署重启与换机手册.md)。

YouTube 使用统一多平台会话架构，安装、启动、撤销和故障处理见 `docs/operations/003-多平台受控会话运行手册.md`。本页只记录 YouTube 特有约束。

## 1. 访问上下文

- Provider Profile：`youtube`
- 会话版本：`browser`
- 会话来源：生产 Runner 每次操作读取独立 YouTube 文件；macOS 宿主维护进程在请求外更新该文件
- 隔离服务：`youtube-operator-runner`
- Chrome 域：`youtube.com`、`youtube-nocookie.com`
- Player 客户端：`mweb`
- POT Provider：固定 OCI digest 的 bgutil sidecar

生产请求不会先尝试匿名再切换账号。启用 `youtube-operator-runner` 并显式设置 `RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}` 后，YouTube inspect 直接进入该 Runner；download 必须使用 inspect 冻结的同一上下文。会话失败返回稳定错误，不能改走匿名或其他账号。

## 2. 生产来源维护

在 Chrome `Default` Profile 已登录 YouTube、且实际执行宿主已经获得 macOS Chrome 数据读取权限后，从 `backend/` 启动维护进程：

```bash
cd backend
uv run python -m app.runner.provider_session_maintainer start
uv run python -m app.runner.provider_session_maintainer status
```

`start` 是幂等命令：先同步采集和校验一次，失败时不启动后台进程；成功后脱离项目生命周期，每 60 秒只比较 YouTube 域数据。发生变化时用锁、`fsync` 和原子替换更新 `.provider-sessions/youtube/cookies.txt`；读取、校验或发布失败保留上一份来源。状态与 PID 位于 `~/Library/Caches/FrameFetch/youtube-session-maintainer`，目录 0700、文件 0600，`status` 只输出 `running/stopped` 和稳定结果码。

维护器不打开网页、不处理登录/验证码、不访问其他平台 Cookie，也不进入 API、下载请求或 Docker。Runner 只读生产文件并为每次操作创建 tmpfs jar。停止维护时保留生产来源：

```bash
uv run python -m app.runner.provider_session_maintainer stop
```

不要把 Python 直接配置为读取 Chrome 的 LaunchAgent。macOS TCC 授权归属于实际责任进程；系统启动的 Python 不继承 VS Code、ChatGPT 或终端的 Full Disk Access。本机已验证该路径返回 `provider_session_permission_denied`。机器重启后必须从已授权的宿主再次运行幂等 `start`，再启动 Compose；普通项目、Docker 或 Runner 重启不会终止维护进程。

开发和生产均需启用 `youtube-operator` Profile，不会因配置了端点自动启动。Linux 或无人桌面部署继续使用由部署者管理的单平台文件，不运行此 macOS 维护器。

### macOS 生产部署

用户明确授权后，可以从当前 Chrome 显式采集 YouTube 的单平台文件。采集仅在来源安装或失效维护时执行，生产 Runner 不读取 Chrome。在私有 `.env.prod` 设置：

```dotenv
COMPOSE_FILE=docker-compose-prod.yml
COMPOSE_PROFILES=youtube-operator
RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}
```

已有其他 profile 或默认策略时合并保留，不能覆盖。首次启动和整机重启先运行本节维护器 `start`，再执行 `docker compose --env-file .env.prod up -d --no-build`。生产只有一个 Compose 文件，容器只读挂载该平台文件，不持有 Chrome 数据库、密码或其他网站会话。

账号退出、平台撤销或新机授权仍需人工重新验证；维护器不会恢复已撤销授权。此时保留准确的 `provider_session_expired`，修复来源后执行一次 `refresh` 和真实 metadata/media，不重启全部服务。

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
