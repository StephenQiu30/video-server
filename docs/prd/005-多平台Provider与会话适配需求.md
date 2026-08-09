# 005 多平台 Provider 与会话适配需求

- 状态：Draft
- 日期：2026-08-10
- 关联 Design：`docs/design/005-多平台Provider策略设计.md`
- 前置调研：`docs/research/003-多平台下载会话与GitHub适配调研.md`

## 1. 背景

当前系统能识别 17 个 Provider，并已对 Bilibili、抖音和小红书部分公开样本完成真实验证；但 Provider 目录没有表达实时可用性、会话、请求证明、出口信誉或账号权益。用户提交 YouTube Shorts 后，平台要求登录/机器人验证，系统却只返回“Cookie 上传不支持”。

Cookie 是平台适配的合法技术手段，不应被一刀切禁止；同时它等同账号会话，不能作为普通字符串穿过 API、数据库、队列和共享工作区。本需求要求把 Cookie 改造成受控 Provider 会话，并与 PO Token、client、User-Agent、固定出口、限流和错误模型共同治理。

## 2. 用户与场景

### 2.1 下载用户

- 下载其有权处理的公开、非 DRM 单视频或短视频。
- 在平台需要会话时得到准确、可行动的提示，而不是泛化 502 或错误的禁用说明。
- 查看 Provider 当前验证状态和最近验证时间。
- 第二阶段可为 allowlist Provider 创建、查看状态和撤销自己的凭据，但不能回读 Cookie。

### 2.2 运维/管理员

- 为 YouTube 维护专用账号 Cookie、固定出口和可选 POT Provider。
- 查看匿名、会话、POT、出口和引擎维度的 canary，不暴露 Secret。
- 原子轮换、回滚、撤销会话，并在 Provider 被 challenge 时停止放大请求。

### 2.3 安全与工程人员

- 证明 Cookie 不进入业务数据面、日志、共享卷或其他 Provider 命令。
- 以固定 Profile、引擎、插件版本和许可证审计每个平台。
- 在 extractor 或平台变更时通过稳定错误与 canary 定位回归。

## 3. 产品目标

1. 修复 YouTube 当前 access verification 失败链，支持受控运维 Cookie、自动 POT 和固定出口。
2. 让 Provider 的“已登记、extractor 存在、真实验证、需要会话、暂不支持”成为不同状态。
3. 确保 inspect 与异步下载全过程使用相同访问上下文。
4. 为其他平台提供可审计的匿名、会话、挑战和多媒体适配策略。
5. 在不降低安全边界的情况下，为后续用户 ProviderCredential 和 gallery-dl 引擎留出明确接口。

## 4. 非目标

- 下载用户无权访问、private、会员、购买、follow-only 或 DRM 内容。
- 自动登录、保存账号密码、处理验证码/2FA 或绕过账号风控。
- 任意原始 Cookie 字符串随 inspection/download 请求传输。
- 任意 yt-dlp/gallery-dl 参数、脚本、插件、文件名或输出目录。
- 公共第三方解析服务、MITM、浏览器远程控制或高频代理轮换。
- 本期开放直播录制、频道/播放列表归档和无限批量。

## 5. 发布分层

### Phase 1：受控服务端会话

- YouTube 运维专用 Cookie Secret。
- YouTube EJS、自动 POT Provider、固定出口和 credential 并发限制。
- Provider Profile v2、统一访问上下文、稳定错误和 canary/status。
- Bilibili、抖音、小红书匿名回归；Tier 2 平台 metadata/Range canary。
- 普通 inspection JSON 仍不接受 Cookie 原文。

### Phase 2：用户会话与多媒体扩展

- owner-scoped ProviderCredential、Vault/Broker、显式 `credential_id` 和撤销。
- allowlist 首批候选：YouTube、X、Instagram；每个平台独立安全/法律门禁。
- gallery-dl 独立 Runner 与多媒体 manifest，领域模型先支持一个帖子多个条目。

Phase 2 不因本文存在而自动获得上线授权；必须完成对应验收。

## 6. 功能需求

### FR-005-01 Provider Profile 与能力

- 系统必须为每个 Provider 定义版本化 Profile：域名、引擎、capability、access mode、Cookie 域、client/impersonation、attestation、出口、并发、重试、错误映射和 canary。
- Generic fallback 不得获得任何 Provider Secret。
- redirect 改变 Provider 时必须重新校验 URL、选择 Profile 和访问上下文。

### FR-005-02 ProviderAccessContext

- inspection 必须冻结 Profile、access mode、credential version、egress affinity、client profile、POT Provider 和 engine commit 的非 Secret 引用。
- 下载前重解析、视频流、音频流、probe sample 和远程 probe 必须使用同一个 context。
- context 不可重建或已撤销时必须失败关闭，不得静默换账号、出口或匿名模式。

### FR-005-03 运维会话

- 第一阶段只允许 Profile allowlist 中的 YouTube 使用运维 Cookie。
- Cookie 源必须为 credentialed Runner 的只读 Secret mount，内容不得位于环境变量。
- 每次 Runner 操作必须使用独占 tmpfs 中的唯一 `0600` 可写 jar；download 的重解析、双流和 probe 串行复用，在所有终态删除。
- 新 Cookie 版本必须 canary 成功后激活；支持回滚、retire、needs_refresh 和撤销。
- 运维账号必须无 Premium、会员、购买/租赁和 private share；credentialed inspect/re-inspect 只允许明确不依赖账号权益的公开/非 DRM 内容，未知 availability 也必须拒绝。

### FR-005-04 YouTube 请求证明与出口

- 默认匿名 clients + EJS；只有策略和稳定错误允许时才切换运维会话。
- 格式缺失或 GVS 403 可启用 `mweb` 自动 PO Token Provider，不持久化静态 video-bound token。
- Cookie、POT、client/UA 和出口必须绑定；更换任一项创建新 context。
- 每个运维 credential 初始最多一个 active job；Provider 被 challenge 时冷却而不是放大重试。

### FR-005-05 稳定错误

- 系统必须区分凭据缺失/过期/拒绝/撤销、POT 缺失/不可用/拒绝、出口 challenge、限流、geo、链接失效、private/权益、DRM、extractor 回归、媒体 URL 过期和 fragment 失败。
- inspect 与 download 必须同构映射；Provider 错误不得默认归为 `worker_lost`。
- 公开响应必须给出合法用户动作，但不得暴露账号、Cookie 状态细节、POT、出口或内部路径。

### FR-005-06 Provider 状态

- `GET /api/providers` 必须按 capability/access mode 返回粗粒度状态和最近验证时间。
- 状态至少支持 `unknown/verified/degraded/access_required/rate_limited/blocked/disabled/unsupported`。
- Registry 登记或 extractor 存在不能直接产生 `verified`。

### FR-005-07 Canary

- 使用项目自有或明确授权样本分别执行匿名 metadata、会话 metadata 和每日小文件下载/校验 canary。
- 记录 Profile、engine/POT 版本、access mode、egress affinity 引用、阶段、耗时和稳定错误。
- Canary 不得使用用户 URL/Cookie，不得阻断普通 PR CI；生产状态由独立调度结果驱动。

### FR-005-08 其他平台

- Bilibili、抖音和小红书现有公开链路必须保持回归，不因 YouTube 会话引入 Cookie。
- TikTok、Vimeo、X、Instagram、Facebook、Twitch 和 Reddit 在冻结支持前必须有 metadata + Range canary 和平台专用错误。
- Pinterest、微博、优酷、腾讯视频、Dailymotion、NicoNico 保持 `unknown`，直至真实验证。
- 视频号、快手保持 `unsupported`；不得通过公共中转、MITM 或未审计插件冒充支持。

### FR-005-09 用户 ProviderCredential

- Phase 2 使用独立 multipart API 创建凭据，最大 1 MiB，只接受 Netscape 格式和 Provider 域 allowlist。
- Cookie 原文使用 KMS/envelope encryption 放入 Vault；数据库只保存元数据和密文引用。
- 凭据严格绑定 owner + Provider；不能跨 owner、跨 Provider 或被 Generic 使用。
- API 永远不回显 Cookie；用户可以查看状态和时间并一键撤销。
- 普通 inspection 只接受可选 `credential_id`，继续拒绝 `cookie` 字段。

### FR-005-10 多媒体帖子

- gallery-dl 只能作为独立、固定版本的 Engine Adapter，不能直接导入当前核心或共享任意配置。
- 在领域模型支持 manifest 和多个制品前，Instagram/X/Reddit/小红书图集不得静默只下载第一项。
- 图片/轮播能力与视频能力分别 canary、配额和展示。

### FR-005-11 管理与审计

- 管理员可查看 Profile/version、会话元数据、最近 canary、kill switch 和撤销状态。
- 记录凭据创建、激活、验证、撤销和 lease 的 actor、Provider、非 Secret ID、时间和结果。
- 新插件/sidecar 必须登记固定版本、许可证、SBOM、网络权限和移除方案。

### FR-005-12 前端提示

- 当前截图中的一刀切错误 detail 必须改为具体状态与合法下一步。
- 页面不得用“1000+ 平台”或静态 Provider 清单承诺实时可用。
- 不向普通用户展示 Cookie 导出细节；Phase 2 凭据页面必须明确 Cookie 等同账号会话、风险、用途和撤销方法。

## 7. 非功能需求

### 7.1 安全与隐私

- Cookie、visitor data、PO Token、Authorization、密码和临时路径不得进入 URL、API 响应、数据库明文、outbox、RabbitMQ、MinIO、普通日志、trace、metrics 或共享 `/work`。
- Secret jar 只存在于 Runner 独占 tmpfs，目录 `0700`、文件 `0600`，同一 jar 不并发写，且成功/失败/取消/超时/信号均清理。
- Runner 仍不得获得 DB、MQ、MinIO、Valkey 或 AI Secret，只能获得对应 Provider 的单次、限域会话租约。
- 所有媒体流量继续经拒绝私网的 egress gateway；凭据不能绕过 SSRF 边界。

### 7.2 可靠性

- Cookie、POT、出口或引擎更新采用 canary 后切换，可快速回滚。
- 重试预算跨 yt-dlp、Runner 和 Worker 统一计算；不得形成三层乘法重试。
- 单 Provider/session/POT sidecar 失败不影响 API readiness 或其他 Provider。
- 撤销凭据后 60 秒内停止新租约和活跃使用。

### 7.3 性能与容量

- Provider/credential/egress 均有分布式 token bucket，Runner 有本地 semaphore。
- YouTube 运维 credential 默认并发 1；其他上限必须由真实容量和风控数据批准。
- 状态查询不实时调用第三方平台，P95 目标小于 500ms。

### 7.4 可维护性与供应链

- OpenAPI 是前后端唯一契约；用户不能控制引擎命令。
- yt-dlp、EJS、POT Provider、gallery-dl 和可信插件全部固定 commit/version，并记录许可证与 SBOM。
- Profile 和错误 marker 有单元/契约测试；真实平台 canary 与普通 CI 解耦。

### 7.5 合法使用

- Cookie 只证明会话，不证明下载授权。
- 所有 access mode 仍只处理用户有权访问的非 DRM 内容。
- 共享运维账号实行最小权益；发现 private、会员、购买、权益不足、未知 availability 或 DRM 时，在媒体下载/交付前终止，不尝试换账号规避。

## 8. 成功指标

- 受控 YouTube 样本的 operator-session inspect → re-inspect → 双流下载/单流下载 → remux → ffprobe → SHA 全链路成功。
- YouTube Cookie、POT、IP challenge、EJS 和 DRM 故障能稳定区分，Provider 错误不再归为 `worker_lost`。
- 100% Cookie 泄漏扫描、权限、清理、并发隔离和跨 Provider 测试通过。
- Bilibili、抖音、小红书匿名回归命令不含 YouTube Cookie/POT，结果不退化。
- `GET /api/providers` 与最近 canary 一致，已登记但未验证的平台不显示 `verified`。
- Phase 2 上线时，跨 owner credential 引用 100% 返回 404，撤销在 60 秒内生效。

## 9. 依赖与决策

- 实现前需同步调整 `AGENTS.md`、`SECURITY.md`、根 README 和 backend README 中的一刀切 Cookie 禁令。
- POT Provider 和 gallery-dl 需要许可证/分发评估；未经批准不进入默认生产镜像。
- Phase 1 需要 Secret mount、Runner 独占 tmpfs、Provider 出口 affinity 和分布式 credential 并发控制。
- Phase 2 需要 KMS/Vault、Credential Broker、审计与用户删除/撤销流程。
- 是否允许任何 private/会员/购买内容不在本需求内；如需改变必须另立产品与法律决策。
