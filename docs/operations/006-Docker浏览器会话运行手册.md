# Docker 浏览器会话运行手册

本手册只适用于独立运维账号中、用户有权处理的公开非 DRM 视频。Cookie 等同账号凭据，不得提交 Git、粘贴到日志或交给普通 API。

微信视频号本地开发使用 Session Broker 自管的隔离 `yuanbao.tencent.com` Chrome
Profile。认证读取、域名过滤、原子落盘和持续轮换均由 `start-local.sh` 自动完成；本地启动前不
需要运行导出命令，也不需要复制 Cookie。`.env` 启用视频号路由并确认运维授权后，
直接执行：

```bash
./scripts/start-local.sh
```

启动脚本默认使用 `browser-live` 版本并启动受当前用户 `launchd` 监督的 Session Broker。
Broker 只写入元宝域最小会话；隔离 Chrome 尚未登录时，Broker 自动打开元宝官方
页面并等待登录完成，随后自行生成 Secret。普通
用户无需也不能上传 Cookie，系统也不代填密码、验证码、2FA 或扫码确认。

## 1. 会话获取与轮换

本地 Session 获取只通过自动 Session Broker。生产不可变 Secret 由部署环境的受控
Secret 管理流程提供，不在应用中保留人工导出入口。视频号 Broker 使用仓库外的专属
Profile 和回环 CDP，不读取默认 Chrome Profile，也不把 Profile 挂载到容器。

通常由 `start-local.sh` 自动启动所需 Broker。以下命令只用于单独诊断状态：

```bash
./scripts/provider-session-broker.sh youtube start
./scripts/provider-session-broker.sh wechat_channels start
./scripts/provider-session-broker.sh tiktok start
./scripts/provider-session-broker.sh douyin start
./scripts/provider-session-broker.sh xiaohongshu start
./scripts/provider-session-broker.sh reddit start
./scripts/provider-session-broker.sh x start
./scripts/provider-session-broker.sh instagram start
./scripts/provider-session-broker.sh youtube status
```

Broker 每 15 秒读取一次当前浏览器状态，只发布目标 Provider 域、未过期且满足认证
标记的最小会话，并原子替换固定版本文件。刷新失败会保留最后一个有效快照，日志
不包含 Cookie 值、浏览器 Profile 路径或异常原文。它解决日常浏览导致的 Cookie
轮换，但不能阻止平台撤销会话、账号登出、风控挑战或权益变化；这些情况必须通过
稳定错误和 canary 显式暴露。首次登录尚未完成时 Broker 保持运行并发布
`login_required`。已声明该 Operator 路由时，其 Runner 和 API 保持未就绪，避免把
“进程存活”误报成平台可下载；完成网页登录后 Broker 会自动发布并恢复就绪。

## 2. 配置

`.env` 至少配置：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100","wechat_channels":"http://wechat-channels-operator-runner:19100","tiktok":"http://provider-operator-runner:19100","douyin":"http://douyin-operator-runner:19100","xiaohongshu":"http://xiaohongshu-operator-runner:19100","reddit":"http://reddit-operator-runner:19100","x":"http://x-operator-runner:19100","instagram":"http://instagram-operator-runner:19100"}
YOUTUBE_COOKIE_SECRET_DIR=./.provider-secrets/youtube
YOUTUBE_COOKIE_VERSION=browser-20260815-01
YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
WECHAT_CHANNELS_COOKIE_SECRET_DIR=./.provider-secrets/wechat_channels
WECHAT_CHANNELS_COOKIE_VERSION=
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
X_COOKIE_VERSION=browser-live
X_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
INSTAGRAM_COOKIE_VERSION=browser-live
INSTAGRAM_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
RUNNER_PROVIDER_SESSION_MAX_AGE_SECONDS=120
```

本地 `WECHAT_CHANNELS_COOKIE_VERSION` 留空时，`start-local.sh` 自动注入
`browser-live`；生产环境必须显式选择已审计的不可变版本。

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
  --profile reddit-operator --profile x-operator \
  --profile instagram-operator config --quiet

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile wechat-channels-operator \
  --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator --profile x-operator \
  --profile instagram-operator \
  up -d --build --force-recreate \
  api media-runner worker-download provider-canary \
  youtube-operator-runner wechat-channels-operator-runner \
  provider-operator-runner douyin-operator-runner \
  xiaohongshu-operator-runner reddit-operator-runner \
  x-operator-runner instagram-operator-runner youtube-pot-provider

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile wechat-channels-operator \
  --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator --profile x-operator \
  --profile instagram-operator ps
```

Operator Runner 不映射宿主机端口。启动成功后使用授权 canary 检查解析、最小格式下载、共享 `/work`、SHA-256 与 ffprobe；不要在命令输出中打印 Cookie 文件。

`provider-canary` 必须和 Runner 共同挂载 `runner_work:/work`，并固定
`RUNNER_WORKSPACE_ROOT=/work`。否则真实媒体已下载也会因容器路径不一致被拒绝为
`invalid_artifact_path`。API 的 `/health/ready` 会探测配置中声明的匿名和 Operator
Runner；配置了路由却没启动 Profile 时应返回未就绪。

## 4. 轮换与撤销

重新导出新 version，更新对应 `*_COOKIE_VERSION`，只重建目标 Operator Runner。发生账号警告、泄漏、异常权益扩张或平台规则变化时，立即从路由表移除 Provider、停止 Profile、在平台侧撤销会话，并删除已撤销版本。不要用 launchd Runner 或浏览器远程调试作为故障回退。
