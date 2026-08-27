# 019 用户设备 Edge Agent 与媒体制品导入计划

- 状态：待实施
- 日期：2026-08-12
- 对应需求：`docs/prd/019-用户设备EdgeAgent与媒体制品导入需求.md`
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`

> 范围调整（2026-08-27）：浏览器本地上传、quarantine、Import Worker 和 MP4 晋升由 023 负责；本计划只依赖 023 已完成的“本地 MP4 隔离上传、验证与 Artifact 晋升”子门禁，不等待无关的剧本模型质量验收。Edge 只传输用户显式选择且已经合法取得的 clear 文件；平台会话、网络采集、签名生成、受保护媒体处理和平台 Adapter 全部移出 019。

## 1. 交付策略

按“先核实 023 的 MP4 Artifact Import 子门禁，再增加设备协议和明文文件导入，最后完善受控来源声明”的顺序交付。每一阶段都必须独立可用、可关闭、可回滚；后续能力不得复制上传、验证、Artifact 或分析逻辑。平台网络接入只能另立 Public Provider/Official Connector 设计，不能扩展本计划。

本仓库负责 FastAPI 控制面、PostgreSQL 当前态、MinIO quarantine、Import Worker、Provider 状态、Web 前端和协议契约。Edge Agent 客户端是独立签名发行物；本仓库只保存版本化 JSON/OpenAPI 契约、真值 fixture 和兼容性测试，不新增顶层平行应用目录。

## 2. 前置门禁：023 本地内容上传

1. `023` 的浏览器 MP4、quarantine、multipart、Import Worker、视频 verifier、Artifact 晋升和崩溃恢复子门禁必须有完成证据；不依赖剧本文档/模型质量等无关验收项。
2. 本计划只增加 `edge_import` 所需设备身份、manifest、lease 和来源证明，不复制 023 的上传/验证逻辑。
3. `DownloadSourceKind`、按来源状态机、`media_imports` 和公共上传端口以 023 当前实现为事实；Edge 只增加必要来源与设备字段。

验证：023 Acceptance、现有 URL 下载回归和 Edge 调用公共上传端口的 architecture test。

## 3. Phase A：设备配对与 Edge 导入

1. 实现 Web 配对 challenge、设备注册/list/revoke、Ed25519 请求签名、防重放和版本阻断。
2. 实现 Agent 创建 import、heartbeat、上传会话、complete/fail 和 cancel intent。
3. 将 Edge manifest 接入 023 的同一 quarantine/Import Worker，不增加第二套验证器。
4. 增加设备 lease、attempt/version 乐观并发、离线 TTL、撤销传播与正在运行任务收敛。
5. 增加 Edge Import Profile catalog、minimum/blocked version、kill switch 和协议兼容 fixture。
6. Provider API 分开展示 `verified_import_supported/required_device_profiles` 与平台下载状态；前端完成未配对、离线、需升级、缺 Profile 和 ready 状态。
7. 对 API、日志、trace、RabbitMQ、PostgreSQL、MinIO metadata 和 WebSocket 做敏感字段负面扫描。

验证：owner 隔离、配对重放、签名篡改、时钟偏差、nonce 重放、设备撤销、旧版本、并发完成、过期 lease、上传 URL 越权、尝试覆盖其他 key、离线取消与网络恢复。

## 4. Phase B：微信视频号明文文件导入

1. 固定 `wechat-authorized-file-v1` manifest，只接受用户通过系统文件选择器显式选择的标准 MP4。
2. Agent 不读取微信/元宝进程、浏览器 profile、缓存、网络流量、系统代理或平台 URL；不存在登录、抓取、转换或解密模块。
3. 本地只执行大小、SHA-256、BMFF/保护标记和 ffprobe 预检，再调用 Phase A 的签名上传协议；服务端继续独立复验。
4. manifest 只允许 rights statement、脱敏 declared origin、Agent/protocol version 和不可逆 source fingerprint。
5. 增加非文件选择器来源、损坏/加密 MP4、哈希错误、超限、设备撤销、上传过期和敏感字段负例。
6. 使用项目自有或明确授权文件完成 select → import → Artifact → Analysis → MD/DOCX → WebSocket E2E。
7. Provider UI 只显示“可从用户设备导入文件”；视频号 URL 下载和 canary 保持 `unsupported`。

## 5. Phase C：受控来源声明

1. `declared_origin` 只接受版本化枚举，不接受平台 URL、作品 id 或任意 metadata；来源为空仍可导入。
2. 视频号、红果或其他标签都只说明用户声明的文件来源，不创建 `provider_key`、不写 Provider canary、不提升平台状态。
3. Edge Agent 不访问任何平台域名、App 会话、浏览器 profile、缓存或网络流量；发送侧 deny test 覆盖 Cookie/Token/签名/保护信息/密钥/短时 URL。
4. 使用项目自有 clear MP4 覆盖各标签的 select → import → Artifact → Analysis → 报告/WebSocket，证据只计入 Import Profile。
5. 若未来获得正式下载/导出 API、合同授权和未加密输出，另立 Official Connector Design/PRD/Plan/Acceptance，不复用 019 的 Edge 权限。

## 6. 代码落点

服务端预计按现有职责落位：

```text
backend/app/domain/imports/                 状态、来源、manifest 值对象与规则
backend/app/application/imports/            配对、导入、上传、完成、取消用例与 ports
backend/app/api/routes/edge_devices.py       用户设备管理 API
backend/app/api/routes/media_imports.py      用户导入 API
backend/app/api/routes/edge_agent.py         设备认证 API
backend/app/api/schemas/                     严格公开/设备协议模型
backend/app/infrastructure/database/         import/device repository 与 ORM
backend/app/infrastructure/object_storage.py 单对象 multipart/quarantine 能力
backend/app/workers/imports/                 验证、晋升、恢复与清理
frontend/src/components/                     导入、配对和状态组件
frontend/src/hooks/                          上传、设备与导入状态流程
frontend/src/services/video/                 只由 OpenAPI 重新生成
```

如果实现需要拆分文件，继续遵守单文件约 200 行职责边界。Edge Agent 客户端源码位置由独立发行项目决定，不放入本仓库 `frontend/` 或 Compose。

## 7. 每阶段质量门禁

- 后端：Ruff lint/format、mypy、全量 pytest、architecture/contract/integration 测试。
- 前端：lint、format、TypeScript/Vitest、production build、OpenAPI 无漂移。
- PostgreSQL：空数据卷和已有当前态数据卷幂等执行 `schema.sql`。
- RabbitMQ：ACL、publisher confirm、重复投递、DLQ 和有界回灌。
- MinIO：上传权限负例、quarantine 隔离、晋升幂等、lifecycle 和孤儿清理。
- 安全：Secret/PII 日志扫描、设备 owner 隔离、签名/重放、上传 key 越权、无外网验证沙箱。
- 浏览器：桌面和 390×844、键盘、loading/empty/error/cancel/retry、无横向溢出和无控制台错误。
- E2E：真实完整文件 → Artifact → RabbitMQ Analysis → Agent → 数据库报告 → MinIO MD/DOCX → WebSocket。
- 发布：Agent 安装包签名、SHA-256、SBOM、许可证 NOTICE、可重复构建与升级/撤销演练。

## 8. 开工前输入

本计划必须先取得 023 本地 MP4 子门禁的完成证据。之后各阶段分别需要：

- Phase A：Edge Agent 客户端发行仓库、签名证书和支持操作系统决策；
- Phase B：项目自有或明确授权的明文视频号来源文件，不需要微信/元宝测试会话；
- Phase C：项目自有 clear MP4、来源枚举、内容权利声明文本、隐私说明和开源合规责任人确认。

缺少某来源输入时不阻塞前一阶段；任何来源标签都不能创建或提升 Provider 状态。
