# 005 多平台 Provider 与会话适配计划

- 状态：In Progress；Phase 1 implementation available，production acceptance pending
- 日期：2026-08-10
- 关联 Design：`docs/design/005-多平台Provider策略设计.md`
- 关联 PRD：`docs/prd/005-多平台Provider与会话适配需求.md`
- 关联 Acceptance：`docs/acceptance/005-多平台Provider与会话适配验收.md`

## 1. 实施原则

1. 先修错误链与访问上下文，再接触真实 Cookie；不能用凭据掩盖分类缺陷。
2. 每个 Phase 使用独立小任务、失败测试、Conventional Commit 和可回滚配置。
3. 默认匿名路径始终存在；启用 credentialed path 必须显式 Profile allowlist 和 kill switch。
4. Cookie/POT/出口变更先在自有或授权 canary 验证，不用用户 URL 做运维探针。
5. 不在普通 request/outbox/RPC 中新增 Cookie 字段，不开放原始引擎参数。
6. 真实平台波动不阻断普通 PR CI；发布门禁读取独立 canary 证据。
7. Phase 1 完成不代表 Phase 2 用户凭据或 gallery-dl 自动获准上线。

## 2. Phase 0：治理、基线与许可证

实施状态：代码/文档/SBOM 已完成；真实账号风险确认、production-like threat/leak evidence 待验收。

### 交付

- 将 `AGENTS.md`、`SECURITY.md`、根 README、backend README 和相关 002/006 文档的一刀切 Cookie 禁令改为受控 Provider 会话边界。
- 冻结 Phase 1 只允许 YouTube 运维会话、仅处理用户有权的非 DRM 内容。
- 固定 yt-dlp/EJS commit/version；登记 POT Provider 和候选 gallery-dl 的许可证、SBOM 与移除方案。
- 记录当前用户样本故障、公开匿名 canary、统一出口和现有错误分类基线。
- 完成 Cookie/POT/出口/账号封禁/跨 Provider 泄漏 threat model。

### 验证

- 文档与治理搜索不再出现“所有 Cookie 永远禁止”的冲突真值。
- 许可证清单覆盖 yt-dlp、EJS、curl-cffi、POT 插件、可信 extractor 插件和可选 gallery-dl。
- 现有无 Cookie 单元/集成测试保持通过，并明确标记为 anonymous path。

## 3. Phase 1：错误 taxonomy 与 Provider Profile v2

实施状态：Profile、context、错误链、API 映射和契约测试已完成；跨 Provider redirect 独立 re-admission 尚未完成。

### 交付

- 扩展 `ProviderProfile`：capability、access mode、Cookie 域、client、attestation、出口、并发、重试、错误映射和 canary。
- 将平台目录拆为按策略族组织的声明式 Profile；URL normalizer、平台运行参数和错误 marker 不再散落在通用命令执行器。
- 以 `ProviderRequest`、`YtDlpCommandBuilder`、有序 `FailureRule` 和 `RunnerInspectionPipeline` 固化 Registry → inspect → download 流水线。
- 新增不可变 `ProviderAccessContextRef`，贯穿 inspection、持久化计划和 Runner download 请求。
- 拆分 credential、POT、egress challenge、rate limit、geo、private/entitlement、DRM、extractor regression 和 media URL expiry。
- 修复 download execution mapping，未知 `provider_*` 不再降为 `worker_lost`。
- 删除 API 的一刀切 Cookie detail，前端按公开稳定码展示合法动作。
- Generic redirect 到已知 Provider 时重新分类；Generic 永不获得凭据。

### 验证

- error-marker table tests 覆盖 inspect/download 的相同 stderr 和返回码。
- 下载前重解析的 `credential_required` 为非重试 Provider 终态，而非 Worker 基础设施故障。
- Profile snapshot/contract 测试覆盖 17 个 key，并区分 registered、verified 和 unsupported。
- request body 直接附加 `cookie` 仍返回 422。

## 4. Phase 2：Runner Secret 边界

实施状态：只读版本源、Runner-only tmpfs、权限/域验证、操作级 jar 和 Compose 隔离已完成；SIGTERM/restart 与全系统泄漏扫描仍待 production-like 验收。

### 交付

- `RunnerSettings` 只增加 allowlist Secret 路径、会话临时根和非 Secret version id；不增加 Cookie 内容环境变量。
- Compose 新增只读 YouTube Secret mount 和 Runner 独占 tmpfs `/run/provider-secrets-tmp`，mode `0700`。
- 启动验证 Netscape header、普通文件、no symlink、最大 1 MiB 和 YouTube 域 allowlist。
- 增加 per-operation context manager：唯一目录、`0600` Cookie jar；初次 inspect 独立销毁，download 的重解析/双流/probe 串行复用并在所有终态 `finally` unlink。
- Secret 源使用不可变 version path，旧 version 保留到 inspection TTL 和最大排队窗口结束；任务不得改用当前 active 版本。
- 确保 Cookie 文件不出现在共享 `/work`、API/Worker 容器、命令输出、日志或错误。
- 按 Runner pool 隔离 anonymous 与 YouTube operator path；非 YouTube 命令无法解析或挂载该 Secret。

### 验证

- 成功、非零退出、timeout、cancel、SIGTERM、workspace limit 和 Runner restart 均无临时文件残留。
- 并发操作获得不同 inode/path，同一 jar 无并发 writer，文件权限严格为 `0600`，源文件内容和 mtime 不变。
- 敏感 fixture 扫描 DB、RabbitMQ、MinIO、日志、trace、API snapshot、container env 和 `/work` 均无命中。
- Runner 仍无法连接 DB/MQ/MinIO/Valkey 或绕过 egress proxy。

## 5. Phase 3：YouTube 运维 Cookie 全链路

实施状态：三条 yt-dlp 路径、快照传递、匿名→运维路由、权益 metadata fail-closed、本地单并发和轮换旧版本引用已完成；真实 Cookie E2E、自动权益漂移停用、版本 canary 状态机和分布式并发尚未完成。

### 交付

- YouTube Profile 支持 `anonymous → operator_managed` 的受控 precedence 和 kill switch。
- `MediaCommands.inspect`、`download_stream`、`download_probe_sample` 统一追加临时 `--cookies`；受会话保护的 remote probe 通过 yt-dlp 或同 context HTTP 层访问。
- Download Worker 保存/复用同一 profile、credential version、client 和 egress affinity 引用。
- 增加 credentialed metadata 权益分类：只允许明确 `public/unlisted` 且不依赖账号权益；unknown/private/premium/subscriber/needs_auth/DRM 在任何媒体下载前拒绝。
- 运维账号基线检查无 Premium、频道会员、购买/租赁、private share 和个人资产；发生漂移立即 disable。
- 会话版本状态机：`pending → canary → active → retired/rejected`，支持 needs_refresh、原子切换和回滚。
- 每 credential subject 分布式并发限制为 1；Runner 本地 semaphore 作为最终门禁。
- 提供部署 Secret 导入/轮换 runbook，明确专用账号、官方导出流程、账号风险和撤销。

### 验证

- 当前失败类别的受控 YouTube 样本完成 inspect → 创建任务 → re-inspect → 下载 → remux → ffprobe → SHA。
- inspection 与 download 的 context 引用完全一致；人为更换出口/client/version 返回 `client_context_mismatch`。
- 初次 inspect 的临时 Cookie 更新不进入业务面；download 从原 version 重建 jar、重新 inspect，并在后续命令中保留该操作内更新。
- 过期、rotated、rejected 和 revoked Cookie 得到不同稳定结果，均不进入 Worker 重试循环。
- 公开、unlisted、private、premium、subscriber、needs_auth、unknown 和 DRM fixture 的权益判定全部通过；被拒绝项没有媒体字节或对象产出。
- Bilibili、抖音、小红书和 Generic 命令行不含 `--cookies`。

## 6. Phase 4：PO Token、固定出口与统一重试预算

实施状态：固定版本插件/sidecar、内部网络、YouTube mweb 参数、非 Secret context 引用和初步错误分类已完成；真实 token/session/proxy binding、刷新一次、`Retry-After` 与统一重试/cooldown 尚未完成。

### 交付

- 以独立 sidecar 方式接入固定版本 bgutil POT Provider；只允许 credentialed YouTube Runner 访问。
- 对明确 GVS/POT 失败使用 `mweb` 自动 token；token 不写 DB/队列/日志，不长期缓存 video-bound 值。
- POT sidecar 获取 token 时继承同一 proxy/source/session binding。
- 统一 yt-dlp、Runner、Worker 重试预算，支持 `Retry-After`、指数退避、jitter 和 Provider cooldown。
- 出口 affinity/health 和 credential health 分开；bot challenge 不被自动翻译为 Cookie 失效。
- 保留 POT 与 credential kill switch，匿名主链可独立回滚。

### 验证

- sidecar 停止、超时、错误 token、一次刷新成功/失败和出口 challenge 得到不同错误。
- POT mint 与视频请求使用同一出口；人工制造 mismatch 被拒绝。
- 三层合计尝试次数不超过 Profile 预算；同一 credential 实际并发不超过 1。
- SBOM、NOTICE 和镜像扫描列出插件及许可证，未登记插件在 CI 被拒绝。

## 7. Phase 5：Capability Canary 与状态页

实施状态：`GET /api/providers`、生成客户端、受保护状态页、持久化结果表、定时 metadata/media 执行器、阈值/恢复迟滞与动态聚合已完成；授权目标、能力/完整视频 Agent E2E gate、低基数指标、自动 kill switch 与各平台真实证据尚未完成。

### 交付

- 建 Provider/capability/access-mode canary 结果表和状态聚合器。
- 匿名/运维 metadata 每 6 小时、小文件 download/remux/probe/SHA 每日执行。
- 首批矩阵：YouTube anonymous/operator/POT；Bilibili、抖音、小红书 anonymous；Generic direct/HLS/DRM fixture。
- 第二批矩阵：TikTok、Vimeo、X、Instagram、Facebook、Twitch、Reddit metadata + Range。
- 第三批：Pinterest、微博、优酷保留版本化匿名公开单视频 Profile；腾讯视频保留识别用 Profile 但状态固定为 `disabled`，重新开放须先满足 024 的官方授权与权益边界。
- 排除清单：AcFun、Rutube、VK Clips、Dailymotion、NicoNico；不登记且相关域名 fail closed。
- 新增 `GET /api/providers` 和前端 Provider 状态/最近验证时间；错误页使用真实状态。

### 验证

- 状态机阈值、恢复迟滞、kill switch 和单 Provider 降级有确定性测试。
- API 不泄露 canary URL、账号、credential version、POT 或出口地址。
- Canary 失败不改变整体 readiness，不影响无关 Provider。
- 视频号以 `wechat-channels-public-v2` / `degraded` / anonymous-only 显示，且仅接受 `/sph/` 直接公开 clear 媒体；快手以 `kuaishou-public-v1` 公开链显示，两者的无效或受保护输入都不得回退 Generic。

## 8. Phase 6：其他平台专用 Profile

实施状态：16 个可下载 Profile 与逐平台上游策略已登记。Bilibili/抖音/小红书沿用 2026-08-07 历史回归，快手沿用 2026-08-11 真实回归；视频号已登记 `wechat-channels-public-v2` 匿名降级链路但真实 clear 媒体门禁仍待完成，腾讯视频保持 `disabled`。其余平台的当前版本 metadata + media + 完整视频 Agent E2E 尚未执行。AcFun、Rutube、VK Clips、Dailymotion 和 NicoNico 已从注册表移除并显式拒绝。

按真实 canary 证据逐个平台交付，不一次性启用所有 Cookie：

1. TikTok：历史 web challenge/`sid_tt` 方案已废弃；当前 v3 仅调用第一方 Player，并分类内容失效、临时 API 失败与 schema 回归。
2. Vimeo：impersonation、Referer、password 与 login 分开建模。
3. X/Instagram/Facebook：公开单视频优先；登录墙、NSFW/private、频控和 schema 回归分离。
4. Twitch/Reddit：公开 clip/VOD/post；subscriber/quarantine/processing 分离。
5. Bilibili/抖音/小红书：保持公开链，只有新需求和安全评审后才增加会话。
6. 视频号：只执行第一方匿名 `/sph/` clear 媒体链路；保护材料、未公开媒体与无效链接 fail closed，不增加 Cookie 或浏览器回退。
7. 腾讯视频：仅保留识别与稳定禁用状态；没有 024 批准的官方授权/API 前不进入 Runner。

每个平台必须先交付：Profile、域名/Cookie allowlist、固定参数、错误 marker、anonymous canary、会话 canary、限流和 kill switch。缺一项则保持 anonymous/disabled。

## 9. Phase 7：用户 ProviderCredential

实施状态：Not started；仍属 Phase 2 产品范围。

### 交付

- 独立 Vault/KMS envelope encryption 和 Credential Broker；主 DB 只存密文引用及元数据。
- 认证 + CSRF 的 multipart create/list/revoke API；OpenAPI operationId 和生成前端服务。
- owner + Provider + credential id 强绑定，租约一次性、短时、限域，不经 Worker/RabbitMQ 解密。
- 凭据 UI 展示风险、用途、状态、最后验证和撤销，不回显原文。
- inspection 增加可选 `credential_id`；继续拒绝原始 `cookie` 字段。
- 撤销在 60 秒内阻止新 lease 并终止活跃进程；删除/保留策略与隐私文档一致。

### 验证

- 跨 owner/Provider 引用返回 404 且 Runner 未被调用。
- Vault/Broker 停止、KMS 失败、租约过期、重复撤销和 Runner crash 有稳定结果。
- 备份、日志、trace、事件和数据库 dump 扫描不到 Cookie 明文。
- 用户凭据不会被 operator/anonymous/Generic pool 复用。

## 10. Phase 8：gallery-dl 与多媒体模型

实施状态：Not started；仍属 Phase 2 产品范围。

### 交付

- 先扩展领域模型：一个 source 可产生受限条目 manifest 和多个制品，保持大小/数量/TTL/owner 隔离。
- gallery-dl 作为独立固定版本 OCI Runner，只开放可信 extractor/profile，输出 schema 化 manifest。
- 首批候选仅为 Instagram/X/Reddit 的公开图片/轮播；时间线、stories、saved/bookmarks 另立范围。
- Engine router 在 URL/Capability 级选择 yt-dlp 或 gallery-dl，不对同一任务无界 fallback。
- 完成 GPL-2.0 分发、源码提供、NOTICE 和运维隔离评估。

### 验证

- 图集不丢条目、不越过 manifest 上限，部分失败语义明确。
- gallery Runner 无视频 Runner Cookie、无 DB/MQ/MinIO Secret、无任意配置。
- 单视频主链性能、格式选择和错误契约不退化。

## 11. 测试与证据矩阵

平台目录管理已于 2026-08-12 纳入 Phase 1：增加 PostgreSQL 目录表、管理员 CRUD、公开状态投影、OpenAPI 生成客户端和 `/admin/providers` 响应式维护页。验证必须覆盖非管理员 403、重复 key、逻辑删除/恢复、目录排序/隐藏、自定义条目不获得系统能力，以及桌面/移动导航。

| 层次 | 必测内容 | 证据 |
| --- | --- | --- |
| Unit | Profile、domain allowlist、错误 marker、context equality、权限/cleanup | pytest 输出 |
| Contract | API/RPC/消息无 Secret、稳定 error code、OpenAPI | contract snapshot |
| Integration | Secret mount/tmpfs、并发、轮换、撤销、Broker/POT 故障 | 容器测试日志 |
| Security | symlink、oversize、跨 Provider、跨 owner、redirect、日志/卷泄漏 | 扫描报告 |
| Provider canary | metadata、Range、完整小文件、remux/probe/SHA | 时间戳结果 |
| E2E | 浏览器解析、格式、任务、下载、状态页 | 浏览器与 API 证据 |
| Supply chain | 固定版本、许可证、SBOM、镜像/Secret scan | CI artifact |

## 12. 风险与回滚

| 风险 | 控制 | 回滚 |
| --- | --- | --- |
| 账号被 challenge/封禁 | 专用账号、并发 1、固定出口、冷却 | disable operator mode，保留匿名状态 |
| Cookie 泄漏 | 独占 pool/tmpfs、无业务面 Secret、扫描 | 撤销/轮换，停池，执行事件响应 |
| POT 插件回归 | 固定版本、sidecar 隔离、独立 canary | 关闭 POT Profile，不影响匿名/其他平台 |
| 平台 schema 变化 | 细分错误、canary、固定提交 | kill switch 或回退上一镜像/Profile |
| 重试放大风控 | 统一预算、credential/egress token bucket | 将 Provider 置 blocked/cooldown |
| GPL/AGPL 合规 | 不复制参考项目代码、独立组件评审 | 移除可选 sidecar/engine |

## 13. 建议提交拆分

```text
docs(provider): 冻结多平台会话边界
refactor(provider): 增加访问上下文和能力模型
fix(runner): 细分平台访问错误
fix(worker): 保留下载阶段平台错误
feat(runner): 增加运维会话临时文件隔离
feat(provider): 接入YouTube受控会话
feat(provider): 接入YouTube请求证明服务
feat(provider): 增加能力探针与状态接口
feat(credentials): 增加用户平台凭据保险库
feat(provider): 增加多媒体引擎适配器
```

每个提交必须可独立验证和回滚，不把示例机械合并为一个大变更。

## 14. 完成定义

- 对应 Phase 的 Acceptance 项全部勾选并附日期、环境、commit、engine/Profile 版本和可复现证据。
- 后端门禁、OpenAPI 生成、前端门禁、Compose config、镜像 build 和相关真实 E2E 全部通过。
- 没有 Cookie/POT/URL 泄漏，没有未接受 Critical/High 风险，没有未登记许可证。
- Provider 页面只展示 canary 支持的能力；未知/失败项保持准确状态。
- Phase 1 与 Phase 2 的上线结论分别记录，不能用本地 Cookie 成功替代生产安全门禁。

截至 2026-08-11，Phase 1 的实现可以进入受限 production-like 验收，但尚不满足上线完成定义：真实 YouTube Cookie/POT E2E、授权 Provider canary、完整视频 Agent E2E gate、全系统泄漏扫描、账号权益漂移停用、分布式单并发和统一重试预算没有完整证据。Phase 2 保持未开始。
