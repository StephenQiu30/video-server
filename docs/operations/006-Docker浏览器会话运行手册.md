# Docker 浏览器会话运行手册

本手册只适用于独立运维账号中、用户有权处理的公开非 DRM 视频。Cookie 等同账号凭据，不得提交 Git、粘贴到日志或交给普通 API。

项目不运行常驻浏览器或 Session Broker。首次授权或第一方明确撤销会话后，执行一次
对应 Provider 的授权命令；认证读取、域名过滤和原子落盘自动完成，用户不复制 Cookie：

```bash
./scripts/authorize-provider-session.sh wechat_channels
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
```

授权命令只在执行期间打开隔离的元宝官方窗口，检测到有效认证并生成最小 Secret 后
立即关闭。业务 Compose 只挂载 Secret，不启动、保持、监控或读取 Chrome。
系统不代填密码、验证码、2FA 或扫码确认，普通用户不能通过 API 上传 Cookie。

## 1. 会话获取与轮换

所有本地 Session 只通过一次性授权命令获取；生产不可变 Secret 由部署环境的受控
Secret 管理流程提供，不保留人工导出入口。视频号授权使用仓库外的专属 Profile 和
回环 CDP，不读取默认 Chrome Profile；其他平台只在显式命令执行期间读取一次当前
浏览器并按 Provider 域最小化。授权结束后没有浏览器监控、CDP 或 Broker 进程运行：

```bash
./scripts/authorize-provider-session.sh youtube
./scripts/authorize-provider-session.sh wechat_channels
./scripts/authorize-provider-session.sh tiktok
./scripts/authorize-provider-session.sh douyin
./scripts/authorize-provider-session.sh xiaohongshu
./scripts/authorize-provider-session.sh reddit
./scripts/authorize-provider-session.sh x
./scripts/authorize-provider-session.sh instagram
```

Runner 只读挂载一次性生成的最小会话，并在第一方请求中验证真实有效性；平台撤销
会话、账号登出、风控挑战或权益变化通过稳定错误和 canary 暴露，不通过后台浏览器
轮询。重新授权会原子替换同一版本文件，随后只重建对应 Runner。

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
RUNNER_PROVIDER_SESSION_MAX_AGE_SECONDS=0
```

本地 `WECHAT_CHANNELS_COOKIE_VERSION` 留空时，Compose 自动使用
`browser-live`；该名称只标识当前登记版本，不代表存在浏览器进程。生产环境必须显式
选择已审计的不可变版本。

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
