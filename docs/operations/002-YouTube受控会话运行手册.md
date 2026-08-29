# YouTube 受控会话运行手册

- 状态：Implementation available；production acceptance pending
- 日期：2026-08-10
- 最近更新：2026-08-30
- 关联 Design：`docs/design/005-多平台Provider策略设计.md`
- 关联 Acceptance：`docs/acceptance/005-多平台Provider与会话适配验收.md`

本文只用于项目所有者有权处理的公开、非 DRM 内容。默认 C 端链路是服务端匿名解析：固定 yt-dlp package `2026.8.19`（`yt-dlp --version` 输出 `2026.08.19`）/ commit `3a08beaf031ab68f966401ead017ac81fe8486cf`，使用 `youtube-v4` 的 `mweb` + EJS + bgutil POT Provider `1.3.2`，不读取宿主 Chrome/个人浏览器 Profile，不要求用户手工提供 Cookie 或 PO Token。

Cookie 等同账号会话密码，可能被平台轮换，也可能导致账号限制。下文 Operator Secret 流程只适用于部署方明确批准的会话场景，不是公开 YouTube 的默认依赖，更不是 IP bot challenge 的修复手段。不得使用主 Google 账号或开发者/用户个人 Cookie，不得把 Cookie 粘贴到普通 API、Issue、日志、命令参数或验收文档。

## 1. 启用前门禁

默认公开链路必须满足：

- Compose 中 `youtube-pot-provider` 锁定为 `brainicism/bgutil-ytdlp-pot-provider:1.3.2@sha256:9a96e6385ce1928da87dea07b1cab0413d2cf8c07a3b8a8bd419f53df2c3843c`，不使用浮动 tag。
- Runner readiness 校验 yt-dlp package 版本/锁定源 commit 和 bgutil 插件版本。Sidecar 不参与 API/公共 Runner readiness，也不作为 Compose `service_healthy` wait gate。容器 PID1 是版本库托管的 supervisor：按精确 `1.3.2` 校验 `/ping`，连续 3 次失败后才重启上游子进程；上游子进程 stdout/stderr 均设为 `ignore`，不让 PO Token 或绑定标识进入持久容器日志。每个 YouTube yt-dlp 子进程启动前还执行独立的 2 秒语义预检，只接受无重定向的 HTTP 200、JSON object 和精确 `1.3.2`；失败进程结束后再检查一次以关闭运行中断裂竞态。失败只返回 `pot_provider_unavailable` 并降级 YouTube，不改变公共 readiness 或其他平台。
- 生产 `RUNNER_PROVIDER_EGRESS_PROXIES` 显式为 `youtube` 配置部署方自身运维、长期稳定且合规的内部出口网关。未配置时实际使用共享 `default` egress，不得声称 YouTube 已具备 C 端稳定可用性。
- 不使用公共代理、WARP/Tor、公共 cobalt/Invidious 或宿主 Chrome 作为故障降级链路。

只有显式启用 Operator Profile 时，专用账号才需满足以下条件，任一项未知都不得启用：

- 无 YouTube Premium、频道会员、购买/租赁、private share、支付方式、个人邮件用途或私人播放列表。
- 只用于项目自有或明确授权的公开 canary，初始每次只运行一个任务。
- Cookie 从独立私密浏览器会话导出，只包含 `youtube.com` 或 `youtube-nocookie.com` 域，格式为 Netscape Cookie File，大小不超过 1 MiB。
- 已确认固定出口和账号风险；当前出口若仍处于 bot challenge，不把真实账号会话投入高并发重试。
- 已记录 yt-dlp commit、EJS、POT Provider、Profile version 和脱敏 egress affinity，不记录账号、Cookie、完整 URL 或出口地址。

项目运行时不会读取开发者或用户的 Chrome Profile，也不会借助 Codex/AI Worker 获取
YouTube Cookie。匿名公开视频不需要会话；确需 Operator 的部署由运维在仓库外通过
受控 Secret 管理流程提供专用账号的最小、不可变版本，不把个人登录态作为服务依赖。

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
RUNNER_PROVIDER_EGRESS_PROXIES={}
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

以上 Operator 配置不替代 YouTube 专用出口。面向 C 端的生产部署还需把由部署方管理、在 Runner 网络中可达的无 URL 内嵌凭据网关写入映射，例如：

```dotenv
RUNNER_PROVIDER_EGRESS_PROXIES={"youtube":"http://youtube-egress-gateway:3128"}
```

`youtube-egress-gateway` 是部署环境占位名，不是本项目自动创建的公共代理。正式值必须是运维方拥有、可审计且符合平台与当地法律的稳定出口。

先只解析配置，再启动显式 Profile：

```bash
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator config --quiet
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator up -d --build
docker compose --env-file .env -f docker-compose.yml --profile youtube-operator ps
```

生产使用独立的 `docker-compose-prod.yml`，其服务拓扑、启动命令、网络、挂载和依赖与 `docker-compose.yml` 保持一致。命令必须显式使用 `.env.prod`：

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator up -d --no-build
~~~

`youtube-operator-runner`、`youtube-pot-provider` 和匿名 Runner 没有可发布的宿主机端口。POT sidecar 只加入 internal `youtube_pot_net`，Runner 的 `runner_egress_net` 同样为 internal；默认拓扑只有 Squid 加入非 internal `proxy_uplink_net`，从网络层阻止 Runner/POT 绕过代理直连。Runner 与 sidecar supervisor 从同一份 `RUNNER_EGRESS_PROXY` / `RUNNER_PROVIDER_EGRESS_PROXIES` 解析实际路由；非法 JSON、带凭据或非法 URL 会在 sidecar 启动前失败且不输出代理地址。Supervisor 只向上游子进程传递选中的 HTTP(S) proxy，固定版本的 bgutil 插件同时在 `/get_pot` 请求体中传递 yt-dlp 当前 `request_proxy`，请求体值优先于环境回退，因此 token mint 和媒体请求使用同一专用代理。生产专用出口必须以部署方受管的双网卡 gateway 加入 `youtube_pot_net`，映射指向该 gateway 的内部服务地址；不得直接填写任意公网代理 hostname。匿名公开链接由服务端自动处理，用户不需要提交 Cookie、PO Token 或额外 yt-dlp 参数。

启动后至少确认：

```bash
docker compose exec -T media-runner yt-dlp --version
docker compose exec -T youtube-pot-provider node -e \
  "fetch('http://127.0.0.1:4416/ping').then(r=>r.json()).then(v=>{if(v.version!=='1.3.2')process.exit(1);console.log(JSON.stringify(v))})"
```

预期分别返回 `2026.08.19` 和 `{"version":"1.3.2"}`。Runner readiness 失败时先修正镜像/依赖漂移，不通过跳过校验恢复流量。`/ping` 连续 3 次失败时由 PID1 supervisor 对上游子进程先发 `SIGTERM`，必要时发 `SIGKILL`，再启动新子进程；只有 PID1 自身退出时才由 `restart: unless-stopped` 拉起容器。该恢复不改变公共 Runner/API readiness。

## 4. Canary 与发布判定

使用项目自有或明确授权的公共样本，分别执行：

1. 匿名 metadata + 1 KiB Range/首 fragment。
2. 运维会话 inspect。
3. 创建下载任务，覆盖 download re-inspect、单流与分离音视频流、remux、ffprobe 和 SHA。
4. 权益反例：private、premium/subscriber、`needs_auth`、unknown availability 和 DRM 必须在任何 stream/artifact/MinIO 写入前终止。
5. 故障反例：缺失、过期、拒绝、撤销 Cookie；POT unavailable/rejected；出口 challenge；429；进程取消与重启。
6. 泄漏扫描：API 响应、DB/outbox、RabbitMQ、MinIO metadata、日志、trace、container env、共享 `/work` 和任务快照均不得出现测试 Cookie/POT/绑定标记。额外确认 sidecar 上游子进程 stdout/stderr 被完全丢弃，容器日志只包含 PID1 supervisor 的固定故障事件。
7. 出口证据：成功/失败都记录实际脱敏 affinity，其值是实际代理 URL 的 SHA-256 前 12 位指纹和 `default` / `provider:youtube` scope；代理 URL 变更后必须观察到新 affinity/context。无 Runner context 的失败记为 `unresolved`，不用 Profile 目标 pool 伪充实际出口。
8. generation 隔离：Runner 通过 HMAC/replay 防护的单次批量接口返回当前非 Secret context，状态只接受其完整 SHA-256 generation：`provider + profile + access mode + credential version + egress affinity + client profile + attestation/POT version + engine commit`。任一字段变化都会立即进入新 canary 周期；旧 generation 即使更晚完成也不得提升或降级当前状态。某个 Runner group 无法在 2 秒内返回有效 context 时，只把对应平台标为 `degraded`，不回退到“最新历史 cohort”。

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
| `provider_auth_required` / `provider_session_expired` | 会话缺失、过期或撤销 | 停止重试；部署方导入新 version 后重新 canary |
| `provider_verification_failed` | POT、EJS、签名或出口验证 | 先检查固定版本、supervisor 固定故障事件和 `/ping`；如仍为 `LOGIN_REQUIRED` / bot challenge，则治理专用出口，不反复更换 Cookie |
| `provider_rate_limited` | Provider/会话/出口限流 | 等待并降低并发；当前实现尚未完成统一 `Retry-After` 预算 |
| `provider_content_restricted` | private 或账号无权益 | 终止，不通过换账号扩大权益 |
| `provider_drm_protected` | DRM | 永久终止 |
| `provider_temporarily_unavailable` | extractor/schema 或 Provider 降级 | 触发工程复核，不归因于 Worker 丢失 |

当前代码已提供受控执行路径、错误分类、配置门禁、默认 POT 拓扑、PID1 连续失败子进程恢复、上游输出隔离、独立 sidecar 网络、命令级 POT 语义预检和实时 runtime-generation 证据过滤。Sidecar 不参与 API/公共 Runner readiness 或 Compose health wait gate。POT 健康不等于 YouTube 可用：当前共享出口仍可能被 bot challenge，必须在合规专用出口上完成授权 metadata/media canary 才能恢复 `verified`。账号权益漂移自动 disable、分布式凭据并发和统一重试预算仍是生产门禁。
