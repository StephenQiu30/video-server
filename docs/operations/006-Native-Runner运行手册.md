# Native Runner 运行手册

本手册只适用于用户有权处理的公开、非 DRM 内容。推荐为 YouTube/TikTok 分别创建无支付、会员和私人数据的专用浏览器 Profile。

## 1. 准备配置

从仓库根目录复制模板，实际文件已被 `.env.*` 规则忽略：

```bash
cp native-runner.env.example native-runner.youtube.env
```

把 `RUNNER_HMAC_SECRET` 改为根 `.env` 的同一值；把 `RUNNER_OPERATOR_BROWSER_SESSIONS` 改为真实专用 Profile。TikTok 使用独立文件，把 Provider 改为 `tiktok`、工作目录改为 `tiktok`、删除 YouTube POT 两项并把端口改为 `19102`。

根 `.env` 配置路由与交付模式：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://host.docker.internal:19101","tiktok":"http://host.docker.internal:19102"}
RUNNER_PRESIGNED_DELIVERY_PROVIDERS=["youtube","tiktok"]
RUNNER_ARTIFACT_DELIVERY_TTL_SECONDS=3600
```

`MINIO_PUBLIC_ENDPOINT` 必须生成 Native Runner 可访问、且与 `RUNNER_ARTIFACT_DELIVERY_ORIGINS` 一致的 URL；本机默认是 `127.0.0.1:19190`。

## 2. 启动依赖与 Native Runner

先启动现有基础拓扑和出口代理。YouTube 原生 PO Provider 按固定的 `1.3.1` 源码构建后在宿主机运行 `node build/main.js`，默认监听 `127.0.0.1:4416`。

```bash
cd backend
uv sync --frozen --dev
uv run --env-file ../native-runner.youtube.env python -m app.runner.native_main
```

另一个终端用 TikTok 配置启动第二个进程。Native 服务只监听 loopback；Docker Desktop 已可通过 `host.docker.internal` 访问宿主机 loopback 服务。

长期运行时不要让 launchd 直接读取 Desktop。把后端运行时、固定版本 PO Provider、环境文件和日志部署到：

```text
~/Library/Application Support/帧取/native-runner
```

LaunchAgent 通过 `NATIVE_RUNNER_ENV_FILE` 指向权限为 `0600` 的 provider 环境文件，`native_main` 会直接读取该文件，不需要把 HMAC Secret 展开进 plist 或进程参数。YouTube、TikTok 和 PO Provider 分别使用独立 label，并设置 `RunAtLoad` 与 `KeepAlive`。

第一次读取 Chrome Cookie 时，macOS 会询问是否允许访问 `Chrome Safe Storage`。账户持有人必须在前台终端执行以下命令，并在系统弹窗点击“始终允许”；命令丢弃读取结果，不会输出密钥：

```bash
security find-generic-password -w -s 'Chrome Safe Storage' >/dev/null
```

不得自动输入 Mac 登录密码、修改钥匙串 ACL、关闭系统保护或给 Node/Python 授予完全磁盘访问权限。

重建 API、下载 Worker 和 Canary 以读取新的根 `.env`：

```bash
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate api worker-download provider-canary
```

## 3. 验证

```bash
curl --fail http://127.0.0.1:19101/health/live
curl --fail http://127.0.0.1:19102/health/live
docker compose --env-file .env -f docker-compose.yml ps
```

随后使用项目自有或明确授权的公开样本完成 inspect、完整下载、ffprobe、SHA、最终 MinIO Artifact 和分析报告。Cookie 失效时停止对应 Native Runner，在专用 Profile 重新登录并更新 session version；不得把 Cookie 粘贴进 `.env` 或 API。

更新代码或固定依赖版本后，先在前台同步到 Application Support 并执行 `uv sync --frozen --no-dev`，再用 `launchctl kickstart -k` 逐个滚动重启。PO Provider 必须核对 tag、commit、SBOM 和 NOTICE，不能跟随 `latest`。
