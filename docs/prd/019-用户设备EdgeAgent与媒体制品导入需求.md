# 019 用户设备 Edge Agent 与媒体制品导入需求

- 状态：需求已定义，代码未实施
- 日期：2026-08-12
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`

> 范围调整（2026-08-27）：浏览器本地文件上传和通用 quarantine/Import Worker 由 `023-本地内容上传与剧本分析` 负责。本需求只保留设备配对和 `edge_import` 明文文件传输；不包含平台会话、网络采集、签名生成、受保护媒体处理或平台 Adapter。Edge 上传必须复用 023 的受控上传与视频验证能力。

> 视频号范围调整（2026-08-26）：`024-微信视频号与腾讯视频授权媒体接入` 取代视频号网络采集需求。Edge Agent 对视频号只传输用户已经合法取得并显式选择的明文文件，不读取微信/元宝会话，不调用私有接口，不安装 CA/代理、不注入、不拦截、不解密。

## 1. 用户目标

用户可以把自己有权使用并已经合法取得的明文视频，通过已配对 Edge Agent 安全导入当前项目并继续使用完整视频 AI 分析、报告、下载历史和任务状态能力。设备上传是制品传输通道，不是平台权益或保护绕过器；平台 Cookie、Token、内容密钥、网络拦截材料和设备签名材料均不进入服务端。

## 2. 成功标准

1. `023` 已通过浏览器 MP4 上传、受控隔离区和 Artifact Import 验收，供 Edge 路径复用。
2. 已配对 Edge Agent 可以上传用户显式选择的单个明文 MP4，服务端从未接收平台会话、网络流量或内容密钥。
3. Edge 导入任务继续使用现有 download ID、历史、WebSocket、Artifact 持久存储和 Analysis API。
4. 视频号来源文件完成 Edge → MinIO → Agent → 报告 E2E 后只证明“用户设备文件导入”，不能把视频号链接下载标记为支持。
5. 红果或其他来源标签的合法明文文件完成 E2E 只证明设备文件导入；不得据此对外标记相应平台链接下载支持。
6. 设备撤销、旧版本阻断、上传中断、校验失败、超限与队列重复投递均能稳定收敛且不留下可读孤儿制品。

## 3. 功能需求

### FR-019-01 复用本地内容导入基础

1. 本需求不得另建浏览器上传、quarantine、multipart、视频 verifier 或 Artifact 晋升实现，必须复用 023 的应用端口与 Worker。
2. `edge_import` 在服务端重新验证实际大小、SHA-256、MP4 容器、视频轨、时长、codec 和配置上限，通过后才创建 Artifact。
3. Edge 来源标签必须显示为“用户设备导入”，不能宣称平台链接已由中心服务下载。
4. 023 未通过本地 MP4 上传和视频验证验收前，不得对外启用 Edge Import Profile。

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
2. manifest 只能包含 Import Profile/Agent 版本、用户声明显示元数据、受控 `declared_origin`、文件指纹、媒体规格、大小、哈希和权利声明；不得包含 `provider_key` 或平台身份断言。
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

### FR-019-06 微信视频号明文文件导入

1. Edge Agent 不接受视频号分享链接作为采集任务；视频号 URL 由 024 识别并返回 `export_required`。
2. 用户必须通过系统文件选择器显式选择其自有原文件或合法取得的标准 MP4；Agent 不读取微信/元宝进程、浏览器 profile、缓存目录或网络流量。
3. Agent 只执行大小、SHA-256、容器/轨道和保护标记预检，再复用签名上传会话；服务端仍独立复验。
4. manifest 只包含脱敏来源声明、权利声明版本、Agent/协议版本和不可逆文件指纹，不包含平台 URL、作品 id、Cookie、token、媒体 URL、密钥或响应原文。
5. 导入结果必须显示为“用户提供的视频号来源文件”，不能显示为平台下载，也不能写视频号 Provider canary。
6. 元宝会话、私有接口、公共 Worker、CA、代理、注入、拦截、`decodeKey` 和受保护媒体转换均无实现或回退入口。

### FR-019-07 红果及其他来源的明文文件

1. 用户只能通过系统文件选择器提交已经合法取得的 clear MP4；`declared_origin=hongguo` 只是审计标签，不是平台身份或下载证明。
2. Edge Agent 不读取 App 会话、设备参数、客户端签名、短时媒体信息、保护信息、缓存或内容密钥，不下载或转换受保护媒体。
3. 服务端只接收标准 MP4、用户声明显示元数据、不可逆文件指纹和权利声明。
4. 文件不 clear、权利声明缺失、媒体身份/哈希不一致或 Import Profile/Agent 版本不匹配时必须 fail closed。
5. 红果创作者/推广中心或未来官方 API 只有取得正式下载/导出接口、合同授权和未加密输出后才能另立 Official Connector，不与 Edge Import 混用。

### FR-019-08 Provider 状态

1. `ProviderAccessMode` 保持 Runner 专用的 anonymous/operator 语义；Edge 使用独立 `verified_import` execution mode 和 `edge_import` source kind。
2. `GET /api/providers` 能区分服务端 extractor、verified import 和 official connector；状态页明确显示所需设备与用户动作，不把设备导入描述为运维会话或平台下载。
3. 微信视频号公开分享链接能力由 025 独立维护，当前为 `wechat-channels-public-v2` / `degraded` / anonymous-only；用户文件导入只展示为独立能力，不能创建、提升或降低视频号及其他 Provider 状态。
4. Import canary 必须按 Import Profile、execution mode、Agent 和客户端版本隔离；只使用项目自有测试设备与自有 clear 文件，不写 Provider canary。
5. 三阶段证据、许可证/SBOM、Secret 流量验收、负例和显式发布批准缺一不可。

### FR-019-09 错误、取消与恢复

1. 设备离线、需升级、文件不可读、上传过期、哈希不一致、媒体损坏、受保护、超限、存储失败和取消均有稳定错误码。
2. 存储和验证瞬时失败只能在统一预算内重试；权利声明缺失、哈希不一致、媒体不合规和版本阻断不得自动重试。
3. 服务端不存在平台采集上下文；Edge 文件选择、读取或预检失败需要用户在设备端重新选择文件或重试上传。
4. 取消必须撤销上传会话、通知仍在线设备终止完整子进程组，并由 TTL 处理永久离线设备。

## 4. 非功能需求

- 单文件大小、视频时长、工作区、并发、请求体、上传会话和任务 lease 使用类型化配置并有安全上限。
- 文件验证进程无公网访问、非 root、固定 ffprobe/FFmpeg 版本并限制 CPU、内存、pids 和执行时间。
- quarantine 独立权限、服务端加密、短 lifecycle；最终 Artifact 延用现有 MinIO 最小权限并持久保存，只允许管理员按明确天数手动清理。
- 新 RabbitMQ 队列使用 quorum、publisher confirm、manual ack、DLQ、有界回灌和幂等 consumer。
- 指标只使用低基数 Import Profile/execution mode/状态标签，不包含 Provider、来源标签、用户、设备、作品、标题或 URL。
- API 变化遵循稳定 operationId、`201 + Location`、严格 OpenAPI schema，并重新生成前端客户端。
- 前端满足既有视觉系统、键盘路径、WCAG 2.2 AA 和 390×844 无横向溢出要求。
- SQL 只修改当前态 `backend/sql/schema.sql`，空数据卷和已有当前态数据卷都必须幂等通过。

## 5. 不在本期

- 任何视频号/红果平台链接采集、批量作者或整剧下载、后台持续监听和定时同步。
- 评论、弹幕、账号关系、榜单、直播和多资产帖子。
- 由服务端保存用户 Provider Cookie、自动登录、自动 2FA 或代表用户取得额外权益。
- 公共解析服务、地域绕过、运维共享平台账号和第三方付费解析 API。
- 红果官方合作 Provider 的具体 SDK 实现；获得正式文档和下载/分析授权后另行细化。
- 跨集聚合分析和多视频 manifest。
