# Docker 浏览器会话运行手册

本手册只适用于独立运维账号中、用户有权处理的公开非 DRM 视频。Cookie 等同账号凭据，不得提交 Git、粘贴到日志或交给普通 API。

## 1. 导出浏览器会话

在浏览器确认 YouTube 与 TikTok 已登录，然后从 `backend/` 分别执行。每次轮换使用新版本名：

```bash
uv run python -m app.runner.browser_cookie_export \
  --provider youtube --browser chrome \
  --version browser-20260815-01 --output-root ../.provider-secrets

uv run python -m app.runner.browser_cookie_export \
  --provider tiktok --browser chrome \
  --version browser-20260815-01 --output-root ../.provider-secrets
```

macOS 可能显示一次 Keychain 授权提示。导出器不会启动后台进程，也不会复制完整 Profile。

## 2. 配置

`.env` 至少配置：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100","tiktok":"http://provider-operator-runner:19100"}
YOUTUBE_COOKIE_SECRET_DIR=./.provider-secrets/youtube
YOUTUBE_COOKIE_VERSION=browser-20260815-01
YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
OPERATOR_PROVIDER_KEY=tiktok
OPERATOR_COOKIE_SECRET_DIR=./.provider-secrets/tiktok
OPERATOR_COOKIE_VERSION=browser-20260815-01
OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
TIKTOK_DEVICE_ID=<每个部署独有且长期不变的19位7开头数字>
```

可用下面的命令生成 device id，并在该部署中持续复用：

```bash
uv run python -c 'import secrets; print("7" + "".join(str(secrets.randbelow(10)) for _ in range(18)))'
```

## 3. 启动与检查

```bash
docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile provider-operator config --quiet

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile provider-operator \
  up -d --build --force-recreate \
  api media-runner worker-download provider-canary \
  youtube-operator-runner provider-operator-runner youtube-pot-provider

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile provider-operator ps
```

Operator Runner 不映射宿主机端口。启动成功后使用授权 canary 检查解析、最小格式下载、共享 `/work`、SHA-256 与 ffprobe；不要在命令输出中打印 Cookie 文件。

## 4. 轮换与撤销

重新导出新 version，更新对应 `*_COOKIE_VERSION`，只重建目标 Operator Runner。发生账号警告、泄漏、异常权益扩张或平台规则变化时，立即从路由表移除 Provider、停止 Profile、在平台侧撤销会话，并删除已撤销版本。不要用 launchd Runner 或浏览器远程调试作为故障回退。
