# YouTube 受控会话运行手册

> ToC 默认使用部署方维护的 YouTube 单平台只读来源。普通客户端不上传 Cookie；个人部署可显式使用隔离 Chrome 与本机 Agent 建立来源。重启与换机步骤见[个人部署手册](008-个人部署重启与换机手册.md)。

YouTube 使用统一多平台会话架构，安装、启动、撤销和故障处理见 `docs/operations/003-多平台受控会话运行手册.md`。本页只记录 YouTube 特有约束。

## 1. 访问上下文

- Provider Profile：`youtube`
- 会话版本：`browser`
- 会话来源：持久库中的加密 YouTube 来源，由 `provider-sources` 原子发布到单平台命名卷；生产 Runner 只读挂载到 `/run/provider-source/cookies.txt`，每次操作重新打开
- 隔离服务：`youtube-operator-runner`
- Chrome 域：`youtube.com`、`youtube-nocookie.com`
- Player 客户端：`mweb`
- POT Provider：固定 OCI digest 的 bgutil sidecar

生产请求不会先尝试匿名再切换账号。启用 `youtube-operator-runner` 并显式设置 `RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}` 后，YouTube inspect 直接进入该 Runner；download 必须使用 inspect 冻结的同一上下文。会话失败返回稳定错误，不能改走匿名或其他账号。

## 2. 生产来源维护

普通用户只提交链接。部署方通过平台允许的方式准备仅含 YouTube allowlist 的 Netscape Cookie 文件，或由 Secret controller 投影该文件；它不是仓库内容，也不复制到每台前端电脑。容器 UID/GID 默认为 `10001`：

```bash
install -d -m 0711 .provider-sessions
install -d -o 10001 -g 10001 -m 0700 .provider-sessions/youtube
install -o 10001 -g 10001 -m 0600 /private/youtube.cookies.txt \
  .provider-sessions/youtube/cookies.txt
```

在私有 `.env.prod` 中显式启用路线；已有其他 JSON 项时合并保留：

```dotenv
COMPOSE_FILE=docker-compose-prod.yml
PROVIDER_SOURCE_ENCRYPTION_KEY=<部署侧稳定密钥，不在终端日志或附件展示>
COMPOSE_PROFILES=youtube-operator
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100"}
RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}
```

```bash
docker compose --env-file .env.prod -f docker-compose-prod.yml \
  up -d --build --force-recreate --wait --wait-timeout 300
```

生产 Runner 只挂载 YouTube 目录，不持有 Chrome 数据库、密码或其他网站会话。每次操作重新读取文件，部署方原子替换后无需重建容器；context generation 会变化，旧 inspection 不得继续执行。

个人部署若需要可显式使用隔离 Chrome 与 Access Agent 导入来源；普通 ToC 用户的解析流程不依赖该工具。新宿主连接同一持久库并配置相同来源密钥，由来源进程自动恢复本机副本；不要靠 Git 同步凭据。账号退出、平台撤销或新出口验证仍需部署方重新建立来源，此时保留准确的 `provider_session_expired`，更新后重新执行真实 metadata/media，不重启全部服务。

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
