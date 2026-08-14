# YouTube 受控会话运行手册

- 状态：Implementation available；production acceptance pending
- 日期：2026-08-10
- 关联 Design：`docs/design/005-多平台Provider策略设计.md`
- 关联 Acceptance：`docs/acceptance/005-多平台Provider与会话适配验收.md`

本文只用于项目所有者有权处理的公开、非 DRM 内容。Cookie 等同账号会话密码，可能被平台轮换，也可能导致账号限制；不得使用主 Google 账号，不得把 Cookie 粘贴到普通 API、Issue、日志、命令参数或验收文档。

## 1. 启用前门禁

专用账号必须满足以下条件，任一项未知都不得启用：

- 无 YouTube Premium、频道会员、购买/租赁、private share、支付方式、个人邮件用途或私人播放列表。
- 只用于项目自有或明确授权的公开 canary，初始每次只运行一个任务。
- Cookie 从独立私密浏览器会话导出，只包含 `youtube.com` 或 `youtube-nocookie.com` 域，格式为 Netscape Cookie File，大小不超过 1 MiB。
- 已确认固定出口和账号风险；当前出口若仍处于 bot challenge，不把真实账号会话投入高并发重试。
- 已记录 yt-dlp commit、EJS、POT Provider、Profile version 和脱敏 egress affinity，不记录账号、Cookie、完整 URL 或出口地址。

推荐导出流程遵循 yt-dlp 官方 YouTube Cookie 指南：在新的私密窗口登录，在唯一标签打开 `https://www.youtube.com/robots.txt`，只导出 YouTube 域 Cookie，随后关闭并不再使用该私密会话。不要自动化密码、2FA 或浏览器 profile。

## 2. 导入不可变 Secret

版本 ID 只使用字母、数字、点、下划线或连字符，例如 `yt-20260810-01`。本地开发目录默认为被 Git 忽略的 `.provider-secrets/youtube/`；生产目录由 Secret 管理器挂载，不能放在仓库、共享 `/work` 或容器环境变量中。

源文件名固定为：

```text
{YOUTUBE_COOKIE_SECRET_DIR}/{YOUTUBE_COOKIE_VERSION}.cookies.txt
```

导入后设置为仅运维用户可读。Runner 启动时会拒绝空文件、symlink、非 Netscape header、超过 1 MiB、非普通文件或包含非 YouTube 域的 Cookie。不要直接修改 active 文件；每次更新创建新版本文件。

## 3. 配置与启动

默认 `.env` 保持：

```dotenv
RUNNER_OPERATOR_BASE_URLS={}
YOUTUBE_COOKIE_VERSION=
RUNNER_OPERATOR_RETAINED_SESSION_VERSIONS={}
YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED=false
```

完成门禁后，在受保护的 `.env`/`.env.prod` 中配置非 Secret 引用：

```dotenv
RUNNER_OPERATOR_BASE_URLS={"youtube":"http://youtube-operator-runner:19100"}
YOUTUBE_COOKIE_SECRET_DIR=./.provider-secrets/youtube
YOUTUBE_COOKIE_VERSION=yt-20260810-01
RUNNER_OPERATOR_RETAINED_SESSION_VERSIONS={}
YOUTUBE_OPERATOR_ACCOUNT_BASELINE_ATTESTED=true
```

先只解析配置，再启动显式 Profile：

```bash
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator config --quiet
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator up -d --build
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator ps
```

生产使用独立的 `docker-compose-prod.yml`，其服务拓扑、启动命令、网络、挂载、依赖和 profiles 与 `docker-compose.yml` 保持一致；不启用 `environment` Profile。命令必须显式使用 `.env.prod`：

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator up -d --no-build
~~~

`youtube-operator-runner`、`youtube-pot-provider` 和匿名 Runner 没有可发布的宿主机端口；POT sidecar 只在内部 `youtube_pot_net` 对运维 Runner 可见。

## 4. Canary 与发布判定

使用项目自有或明确授权的公共样本，分别执行：

1. 匿名 metadata + 1 KiB Range/首 fragment。
2. 运维会话 inspect。
3. 创建下载任务，覆盖 download re-inspect、单流与分离音视频流、remux、ffprobe 和 SHA。
4. 权益反例：private、premium/subscriber、`needs_auth`、unknown availability 和 DRM 必须在任何 stream/artifact/MinIO 写入前终止。
5. 故障反例：缺失、过期、拒绝、撤销 Cookie；POT unavailable/rejected；出口 challenge；429；进程取消与重启。
6. 泄漏扫描：API 响应、DB/outbox、RabbitMQ、MinIO metadata、日志、trace、container env、共享 `/work` 和任务快照均不得出现测试 Cookie 标记。

证据只记录日期、Git SHA、Provider/capability、access mode、Profile/engine/POT version、脱敏 egress ref、阶段、稳定码和证据位置。没有真实媒体 Range/完整下载证据时，不得把 YouTube 标记为 `verified`。

## 5. 轮换、回滚与撤销

轮换不修改旧文件：

1. 导入新 version，离线校验后用授权 canary 验证。
2. 将新 version 设为 `YOUTUBE_COOKIE_VERSION`；把仍有排队任务引用的旧 version 放入 `RUNNER_OPERATOR_RETAINED_SESSION_VERSIONS`，例如 `{"youtube":["yt-20260810-01"]}`。
3. 滚动重启运维 Runner；新 inspection 使用新 version，旧任务只可使用自己冻结的 retained version。
4. 等待 inspection TTL 与最大排队窗口结束，再移除 retained version 和对应只读文件。

出现账号权益漂移、Cookie 泄漏、账号警告、跨 Provider、未知 availability、无法解释的访问扩张或撤销指令时：立即从 `RUNNER_OPERATOR_BASE_URLS` 删除 `youtube`、停止 `youtube-operator` Profile、在 Google 账号侧撤销会话，并移除 active/retained version。不要用匿名、其他账号或新出口自动接管旧任务。

## 6. 故障定位

| 稳定类别 | 含义 | 处理 |
| --- | --- | --- |
| `provider_auth_required` / `provider_session_expired` | 会话缺失、过期或撤销 | 停止重试；导出新 version 后重新 canary |
| `provider_verification_failed` | POT、EJS、签名或出口验证 | 区分 sidecar、EJS 与 IP；不反复更换 Cookie |
| `provider_rate_limited` | Provider/会话/出口限流 | 等待并降低并发；当前实现尚未完成统一 `Retry-After` 预算 |
| `provider_content_restricted` | private 或账号无权益 | 终止，不通过换账号扩大权益 |
| `provider_drm_protected` | DRM | 永久终止 |
| `provider_temporarily_unavailable` | extractor/schema 或 Provider 降级 | 触发工程复核，不归因于 Worker 丢失 |

当前代码已提供受控执行路径、错误分类、配置门禁和可选 POT 拓扑；自动 canary 聚合、账号权益漂移自动 disable、分布式凭据并发、统一重试预算和真实生产验收仍是发布前门禁。
