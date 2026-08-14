# 019 用户设备 Edge Agent 与媒体制品导入需求

- 状态：需求已定义，代码未实施
- 日期：2026-08-12
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`

> 范围调整（2026-08-14）：浏览器本地文件上传和通用 quarantine/Import Worker 由 `023-本地内容上传与剧本分析` 负责。本需求只保留设备配对、`edge_import` 和微信视频号/红果 Adapter；Edge 上传必须复用 023 的受控上传与视频验证能力。

## 1. 用户目标

用户可以把自己有权使用的本地视频，或在自己设备、自己已授权的平台会话中取得的微信视频号/红果单视频，安全导入当前项目并继续使用完整视频 AI 分析、报告、下载历史和任务状态能力。用户不需要把平台 Cookie、Token、内容密钥或设备签名材料交给服务端。

## 2. 成功标准

1. `023` 已通过浏览器 MP4 上传、受控隔离区和 Artifact Import 验收，供 Edge 路径复用。
2. 已配对 Edge Agent 可以上传单个视频号或红果 MP4，服务端从未接收平台会话或内容密钥。
3. Edge 导入任务继续使用现有 download ID、历史、WebSocket、Artifact TTL 和 Analysis API。
4. 微信视频号至少一条授权分享链接完成 Edge → MinIO → Agent → 报告 E2E 后才能对外标记支持。
5. 红果至少一个授权单集在固定 Android/App/Agent 版本上完成同样 E2E 后才能对外标记支持。
6. 设备撤销、旧版本阻断、上传中断、校验失败、超限与队列重复投递均能稳定收敛且不留下可读孤儿制品。

## 3. 功能需求

### FR-019-01 复用本地内容导入基础

1. 本需求不得另建浏览器上传、quarantine、multipart、视频 verifier 或 Artifact 晋升实现，必须复用 023 的应用端口与 Worker。
2. `edge_import` 在服务端重新验证实际大小、SHA-256、MP4 容器、视频轨、时长、codec 和配置上限，通过后才创建 Artifact。
3. Edge 来源标签必须显示为“用户设备导入”，不能宣称平台链接已由中心服务下载。
4. 023 未通过本地 MP4 上传和视频验证验收前，不得对外启用 Edge Adapter。

### FR-019-02 下载任务兼容

1. 远程下载、本地导入和 Edge 导入共享 `download_jobs` 与 `artifacts`。
2. 导入任务使用新的 `source_kind`；远程任务继续要求 inspection/format，导入任务不得伪造 URL inspection。
3. 导入任务的创建、阶段、成功、失败和取消继续写入现有任务事件并可通过 WebSocket 恢复。
4. 导入成功后继续使用现有 `POST /api/downloads/{download_id}/analyses`；AI 失败不改变导入成功状态。
5. 原下载流程、消息契约和用户数据不得因新增来源发生行为回归。

### FR-019-03 设备配对与撤销

1. 配对只能由已登录用户发起，challenge 十分钟内一次有效。
2. 每次安装生成独立 Ed25519 密钥；服务端只保存公钥、设备凭据哈希、owner、版本、能力与状态。
3. 设备请求必须签名并包含防重放 nonce、时间戳和 body hash。
4. 用户可以查看和撤销自己的设备；设备不能读取、更新或完成其他 owner 的任务。
5. 被撤销、被阻断或低于最低版本的 Agent 不能获得新任务或上传会话。

### FR-019-04 Edge 导入协议

1. Agent 本地选择并检查媒体后，提交严格、版本化、拒绝额外字段的脱敏 manifest。
2. manifest 只能包含 Provider/Adapter/Agent 版本、显示元数据、来源指纹、媒体规格、大小、哈希和权利声明。
3. manifest、API、数据库、日志、trace、RabbitMQ 与 WebSocket 都不得包含 Cookie、Token、内容/转换密钥、证书私钥、签名媒体 URL、平台响应或本地路径。
4. 每个上传会话只能写一个确定 quarantine object；过期后必须创建新 attempt，不能扩大原 URL 权限。
5. Agent 只获得 Edge API 和单对象上传能力，不获得 DB、RabbitMQ、AI 或对象存储通用凭据。

### FR-019-05 可靠验证与晋升

1. 上传完成与 023 定义的 `content.import.verify.requested` 必须通过同一 PostgreSQL 事务和 outbox 连接。
2. 独立 Import Worker 使用 lease、heartbeat、幂等唯一键和 deterministic final key 处理至少一次投递。
3. quarantine 对象在验证通过前不能被下载接口或 Analysis Worker 读取。
4. 客户端声明的大小、哈希和媒体信息全部由服务端重新计算；任何不一致都 fail closed。
5. Artifact 行、download succeeded 和任务事件在数据库中一致收敛；崩溃重试不得产生第二个 Artifact。
6. 取消、过期、失败和成功后都必须有界清理 multipart、quarantine 和本地工作区。

### FR-019-06 微信视频号 Adapter

1. 首个 Adapter 只接受 `weixin.qq.com/sph/<id>` 单视频分享链接并使用用户本地元宝会话。
2. 元宝 Cookie、媒体 token 和转换参数只保存在本地；链接解析、下载前重解析、域名 allowlist、超时和重定向上限必须固定在签名 Adapter 中。
3. 媒体可以直接通过 MP4 验证时不得执行额外转换；确需转换时只处理当前任务，任务结束销毁参数和工作区。
4. 本地会话缺失/过期必须返回准确错误并引导用户本地登录，不能调用公共 Worker 或共享运维账号。
5. Windows 微信客户端采集是用户显式选择的回退路径；安装动态 CA 前必须说明影响，异常退出必须恢复代理并支持卸载 CA。
6. 首期一次只处理用户明确选择的一个视频，不支持后台持续监听、作者批量和评论采集。

### FR-019-07 红果 Adapter

1. 首期只支持用户控制的 Android/模拟器、固定验收 App/Agent 版本和单集任务。
2. App 会话、设备参数、客户端签名、短时媒体信息和受保护媒体处理全部留在本地。
3. 服务端只接收标准 MP4、单集显示元数据和脱敏来源指纹。
4. App/Agent 版本不匹配、签名入口变化、作品身份不一致和无内容权利时必须 fail closed。
5. 禁止复制、打包或分发无 LICENSE、许可冲突、来源不明的红果项目源码和二进制。
6. 创作者/推广中心或未来官方 API 使用独立授权 Provider，不与 Android Edge Adapter 混用。

### FR-019-08 Provider 状态

1. `ProviderAccessMode` 增加 `user_device`；`GET /api/providers` 能区分服务端 extractor 和 Edge Adapter。
2. Provider 状态页明确显示所需设备、支持的 Adapter 与用户动作，不把 `user_device` 描述为运维会话。
3. 微信视频号和红果在真实授权 canary 前保持 `unsupported`；仅注册目录、导入本地文件或开源项目测试通过均不能提升状态。
4. canary 必须按 Provider、Adapter/Profile、access mode、Agent 和客户端版本隔离；只使用项目自有或明确授权测试设备。
5. 三阶段证据、许可证/SBOM、Secret 流量验收、负例和显式发布批准缺一不可。

### FR-019-09 错误、取消与恢复

1. 设备离线、需升级、会话失效、Adapter 回归、上传过期、哈希不一致、媒体损坏、超限、存储失败和取消均有稳定错误码。
2. 存储和验证瞬时失败只能在统一预算内重试；权益不足、哈希不一致、媒体不合规和版本阻断不得自动重试。
3. 服务端不保存可重新执行平台采集的会话上下文；Edge 采集失败需要用户在设备端重新发起。
4. 取消必须撤销上传会话、通知仍在线设备终止完整子进程组，并由 TTL 处理永久离线设备。

## 4. 非功能需求

- 单文件大小、视频时长、工作区、并发、请求体、上传会话和任务 lease 使用类型化配置并有安全上限。
- 文件验证进程无公网访问、非 root、固定 ffprobe/FFmpeg 版本并限制 CPU、内存、pids 和执行时间。
- quarantine 独立权限、服务端加密、短 lifecycle；最终 Artifact 延用现有 MinIO 最小权限与 TTL。
- 新 RabbitMQ 队列使用 quorum、publisher confirm、manual ack、DLQ、有界回灌和幂等 consumer。
- 指标只使用低基数 Provider/Adapter/平台/状态标签，不包含用户、设备、作品、标题或 URL。
- API 变化遵循稳定 operationId、`201 + Location`、严格 OpenAPI schema，并重新生成前端客户端。
- 前端满足既有视觉系统、键盘路径、WCAG 2.2 AA 和 390×844 无横向溢出要求。
- SQL 只修改当前态 `backend/sql/schema.sql`，空数据卷和已有当前态数据卷都必须幂等通过。

## 5. 不在本期

- 视频号/红果批量作者或整剧下载、后台持续监听和定时同步。
- 评论、弹幕、账号关系、榜单、直播和多资产帖子。
- 由服务端保存用户 Provider Cookie、自动登录、自动 2FA 或代表用户取得额外权益。
- 公共解析服务、地域绕过、运维共享平台账号和第三方付费解析 API。
- 红果官方合作 Provider 的具体 SDK 实现；获得正式文档和下载/分析授权后另行细化。
- 跨集聚合分析和多视频 manifest。
