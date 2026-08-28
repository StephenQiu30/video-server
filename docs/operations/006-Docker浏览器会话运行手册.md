# Docker 浏览器会话运行手册

本手册只适用于独立运维账号中、用户有权处理的公开非 DRM 视频。Cookie 等同账号凭据，不得提交 Git、粘贴到日志或交给普通 API。

微信视频号使用已登录 `yuanbao.tencent.com` 的 Chrome 会话，导出命令为：

```bash
cd backend
uv run python -m app.runner.browser_cookie_export \
  --provider wechat_channels --browser chrome \
  --version browser-live --output-root ../.provider-secrets
```

导出器要求 `hy_user` 与 `hy_token` 同时存在，并只写入元宝域 Cookie。普通用户无需也不能上传 Cookie。

## 1. 导出浏览器会话

在浏览器确认目标 Provider 已登录，然后从 `backend/` 分别执行。每次轮换使用新版本名；支持 `youtube`、`wechat_channels`、`tiktok`、`douyin`、`xiaohongshu`、`reddit`、`x`、`instagram` 与 `facebook`：

```bash
uv run python -m app.runner.browser_cookie_export \
  --provider youtube --browser chrome \
  --version browser-20260815-01 --output-root ../.provider-secrets

uv run python -m app.runner.browser_cookie_export \
  --provider tiktok --browser chrome \
  --version browser-20260815-01 --output-root ../.provider-secrets
```

macOS 可能显示一次 Keychain 授权提示。导出器不会启动后台进程，也不会复制完整 Profile。

受信任的本地 macOS 开发机可以让项目持续复用当前 Chrome 登录态；从仓库根目录
启动通用桥接：

```bash
./scripts/provider-cookie-bridge.sh youtube start
./scripts/provider-cookie-bridge.sh wechat_channels start
./scripts/provider-cookie-bridge.sh tiktok start
./scripts/provider-cookie-bridge.sh douyin start
./scripts/provider-cookie-bridge.sh xiaohongshu start
./scripts/provider-cookie-bridge.sh reddit start
./scripts/provider-cookie-bridge.sh youtube status
```

桥接每 15 秒读取一次当前浏览器状态，只导出目标 Provider 域、未过期且满足认证
标记的 Cookie，并原子替换固定版本文件。刷新失败会保留最后一个有效快照，日志
不包含 Cookie 值、浏览器 Profile 路径或异常原文。它解决日常浏览导致的 Cookie
轮换，但不能阻止平台撤销会话、账号登出、风控挑战或权益变化；这些情况必须通过
稳定错误和 canary 显式暴露。

## 2. 配置

`.env` 至少配置：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100","wechat_channels":"http://wechat-channels-operator-runner:19100","tiktok":"http://provider-operator-runner:19100","douyin":"http://douyin-operator-runner:19100","xiaohongshu":"http://xiaohongshu-operator-runner:19100","reddit":"http://reddit-operator-runner:19100"}
YOUTUBE_COOKIE_SECRET_DIR=./.provider-secrets/youtube
YOUTUBE_COOKIE_VERSION=browser-20260815-01
YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
WECHAT_CHANNELS_COOKIE_SECRET_DIR=./.provider-secrets/wechat_channels
WECHAT_CHANNELS_COOKIE_VERSION=browser-live
WECHAT_CHANNELS_RETAINED_SESSION_VERSIONS={}
WECHAT_CHANNELS_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
OPERATOR_PROVIDER_KEY=tiktok
OPERATOR_COOKIE_SECRET_DIR=./.provider-secrets/tiktok
OPERATOR_COOKIE_VERSION=browser-20260815-01
OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
TIKTOK_DEVICE_ID=<每个部署独有且长期不变的19位7开头数字>
DOUYIN_COOKIE_SECRET_DIR=./.provider-secrets/douyin
DOUYIN_COOKIE_VERSION=browser-20260818-01
DOUYIN_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
XIAOHONGSHU_COOKIE_SECRET_DIR=./.provider-secrets/xiaohongshu
XIAOHONGSHU_COOKIE_VERSION=browser-20260818-01
XIAOHONGSHU_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
REDDIT_COOKIE_SECRET_DIR=./.provider-secrets/reddit
REDDIT_COOKIE_VERSION=browser-20260818-01
REDDIT_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
```

可用下面的命令生成 device id，并在该部署中持续复用：

```bash
uv run python -c 'import secrets; print("7" + "".join(str(secrets.randbelow(10)) for _ in range(18)))'
```

## 3. 启动与检查

```bash
docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile wechat-channels-operator \
  --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator config --quiet

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile wechat-channels-operator \
  --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator \
  up -d --build --force-recreate \
  api media-runner worker-download provider-canary \
  youtube-operator-runner wechat-channels-operator-runner \
  provider-operator-runner douyin-operator-runner \
  xiaohongshu-operator-runner reddit-operator-runner youtube-pot-provider

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile wechat-channels-operator \
  --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator ps
```

Operator Runner 不映射宿主机端口。启动成功后使用授权 canary 检查解析、最小格式下载、共享 `/work`、SHA-256 与 ffprobe；不要在命令输出中打印 Cookie 文件。

`provider-canary` 必须和 Runner 共同挂载 `runner_work:/work`，并固定
`RUNNER_WORKSPACE_ROOT=/work`。否则真实媒体已下载也会因容器路径不一致被拒绝为
`invalid_artifact_path`。API 的 `/health/ready` 会探测配置中声明的匿名和 Operator
Runner；配置了路由却没启动 Profile 时应返回未就绪。

## 4. 轮换与撤销

重新导出新 version，更新对应 `*_COOKIE_VERSION`，只重建目标 Operator Runner。发生账号警告、泄漏、异常权益扩张或平台规则变化时，立即从路由表移除 Provider、停止 Profile、在平台侧撤销会话，并删除已撤销版本。不要用 launchd Runner 或浏览器远程调试作为故障回退。
