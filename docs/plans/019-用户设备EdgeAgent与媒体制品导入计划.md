# 019 用户设备 Edge Agent 与媒体制品导入计划

- 状态：待实施
- 日期：2026-08-12
- 对应需求：`docs/prd/019-用户设备EdgeAgent与媒体制品导入需求.md`
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`

## 1. 交付策略

按“先证明不依赖平台的 Artifact Import，再增加设备协议，最后逐平台 Adapter”的顺序交付。每一阶段都必须独立可用、可关闭、可回滚；后续 Adapter 不得复制上传、验证、Artifact 或分析逻辑。

本仓库负责 FastAPI 控制面、PostgreSQL 当前态、MinIO quarantine、Import Worker、Provider 状态、Web 前端和协议契约。Edge Agent 客户端是独立签名发行物；本仓库只保存版本化 JSON/OpenAPI 契约、真值 fixture 和兼容性测试，不新增顶层平行应用目录。

## 2. Phase A：领域与契约骨架

1. 新增 `DownloadSourceKind`，为 `download_jobs` 增加来源字段，并把 inspection/format 约束调整为远程必填、导入必须为空。
2. 扩展 Download domain/view/API/history/analytics，使现有远程任务保持原响应，导入任务显示准确来源。
3. 将全局线性下载阶段改成按 source kind 的显式转换表，增加 `awaiting_device/collecting/importing`。
4. 新增 `ProviderAccessMode.USER_DEVICE`，更新数据库 canary constraint、Provider schema 与前端文案。
5. 建立 `edge_devices`、`media_imports`、`media_import_attempts` 的 SQLAlchemy 模型、Repository port 和当前态 SQL。
6. 定义严格的配对、设备签名、manifest、上传和完成协议；所有 Pydantic 模型禁止额外字段。

验证：领域状态机、SQL CHECK、已有数据卷幂等升级、OpenAPI operationId/响应兼容、现有远程下载全量回归。

## 3. Phase B：浏览器原始媒体导入

1. 实现 `POST/GET /api/media-imports`、upload-session/complete 子资源，并让现有 download cancel 级联终止导入和上传。
2. 新增 quarantine bucket/前缀、独立 MinIO 身份、短 lifecycle 和孤儿清理。
3. 新增 `artifact.import.verify.requested` outbox、quorum queue、Import Worker、DLQ 与有界回灌。
4. 抽取并复用现有容器、codec、轨道、时长、大小和 SHA-256 验证规则；验证沙箱禁止外网。
5. 实现 deterministic Artifact 晋升、数据库原子终态和崩溃恢复。
6. 前端增加单 MP4 上传、来源标签、权利声明、上传/验证/失败/取消状态；成功后进入现有下载详情和分析入口。
7. 下载历史和管理员来源统计区分 `browser_import`，但不计入 Provider canary。

验证：最小/最大边界文件、伪扩展名、损坏 MP4、无音频/无视频、多文件、哈希错误、上传中断、重复 complete、重复消息、Worker 崩溃、对象存储失败、TTL 清理，以及完整 Analysis/报告/WebSocket E2E。

Phase B 完成即可独立发布“本地视频导入并分析”，不宣称视频号或红果下载能力。

## 4. Phase C：设备配对与 Edge 导入

1. 实现 Web 配对 challenge、设备注册/list/revoke、Ed25519 请求签名、防重放和版本阻断。
2. 实现 Agent 创建 import、heartbeat、上传会话、complete/fail 和 cancel intent。
3. 将 Edge manifest 接入 Phase B 的同一 quarantine/Import Worker，不增加第二套验证器。
4. 增加设备 lease、attempt/version 乐观并发、离线 TTL、撤销传播与正在运行任务收敛。
5. 增加 Edge Adapter Profile catalog、minimum/blocked version、kill switch 和协议兼容 fixture。
6. Provider API 增加 `edge_adapter_exists/required_device_profiles`；前端完成未配对、离线、需升级、缺 Adapter 和 ready 状态。
7. 对 API、日志、trace、RabbitMQ、PostgreSQL、MinIO metadata 和 WebSocket 做敏感字段负面扫描。

验证：owner 隔离、配对重放、签名篡改、时钟偏差、nonce 重放、设备撤销、旧版本、并发完成、过期 lease、上传 URL 越权、尝试覆盖其他 key、离线取消与网络恢复。

## 5. Phase D：微信视频号元宝分享链接 Adapter

1. 固定 `wechat-yuanbao-share-v1` 协议、第一方域名 allowlist、超时、重定向、最大大小/时长与输出合同。
2. 在 Edge Agent 中实现用户本地元宝会话检查、分享链接解析、下载前重解析和单视频下载。
3. 先执行 MP4 直接验证；仅在需要时执行本地受保护前缀转换，并用独立真值测试验证边界和错误密钥不落盘。
4. 本地 packager 执行 ffprobe/SHA-256 后只发送严格 manifest 与 MP4。
5. 增加未登录、会话过期、链接失效、无视频、媒体 URL 越界、转换失败、哈希错误和版本变化负例。
6. 使用项目自有或明确授权样本完成 capture → import → Artifact → Analysis → MD/DOCX → WebSocket 三阶段 canary。
7. 完成 Agent/Adapter SBOM、逐文件来源与许可证审计，确认未包含公共 Worker、预置凭据或来源不明 WASM。

真实验收通过并显式批准后，微信视频号才可由 `unsupported` 调整为带 `user_device` 的当前支持状态。

## 6. Phase E：Windows 微信客户端回退 Adapter

1. 仅支持一组经过 canary 的 Windows/微信版本矩阵。
2. 实现 per-install 动态 CA、loopback 认证、进程/域名最小代理范围、代理状态快照与异常恢复。
3. 提供安装前说明、显式同意、运行状态和一键卸载 CA；禁止后台默认持续监听。
4. 只采集用户明确选择的单视频并复用 Phase C/D packager/import 协议。
5. 分别验证进程崩溃、系统重启、代理原本已配置、CA 撤销、微信升级和采集失败后的网络恢复。
6. 该 Adapter 单独 canary 和发布，不以元宝路径成功代替。

## 7. Phase F：Android 红果单集 Adapter

1. 获取用户控制的 Android/模拟器、明确授权的单集样本和固定红果 App 版本。
2. 独立实现 `hongguo-android-app-v1`，不复制无许可证参考仓库；建立协议分层、算法真值与来源记录。
3. 本地实现 App 会话/设备绑定、作品和单集选择、下载前媒体重解析、标准 MP4 产出与单任务清理。
4. manifest 只包含单集显示元数据、来源指纹和媒体规格；对设备参数、签名值、保护信息、密钥与短时 URL 做发送侧 deny test。
5. 增加 App 版本变化、设备离线、会话过期、身份不一致、无权益、媒体转换错误、分集错配和超限负例。
6. 完成一集真实 capture → import → Artifact → Analysis → 报告/WebSocket canary、撤销演练、SBOM、许可证与流量审计。
7. 真实验收和显式批准前，红果目录项继续为 `unsupported`。

## 8. 代码落点

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

## 9. 每阶段质量门禁

- 后端：Ruff lint/format、mypy、全量 pytest、architecture/contract/integration 测试。
- 前端：lint、format、TypeScript/Vitest、production build、OpenAPI 无漂移。
- PostgreSQL：空数据卷和已有当前态数据卷幂等执行 `schema.sql`。
- RabbitMQ：ACL、publisher confirm、重复投递、DLQ 和有界回灌。
- MinIO：上传权限负例、quarantine 隔离、晋升幂等、lifecycle 和孤儿清理。
- 安全：Secret/PII 日志扫描、设备 owner 隔离、签名/重放、上传 key 越权、无外网验证沙箱。
- 浏览器：桌面和 390×844、键盘、loading/empty/error/cancel/retry、无横向溢出和无控制台错误。
- E2E：真实完整文件 → Artifact → RabbitMQ Analysis → Agent → 数据库报告 → MinIO MD/DOCX → WebSocket。
- 发布：Agent 安装包签名、SHA-256、SBOM、许可证 NOTICE、可重复构建与升级/撤销演练。

## 10. 开工前输入

Phase A/B 不需要平台账号，可以立即实施。后续阶段分别需要：

- Phase C：Edge Agent 客户端发行仓库、签名证书和支持平台决策；
- Phase D：用户本地元宝测试会话与项目自有/明确授权的视频号分享样本；
- Phase E：Windows 测试机、固定微信版本和允许安装/卸载测试 CA 的环境；
- Phase F：用户控制的 Android/模拟器、固定红果 App 版本和明确授权单集；
- 所有平台阶段：内容权利声明文本、隐私说明和开源合规责任人确认。

缺少某平台输入时，不阻塞前一阶段，但对应 Adapter 只能保留 fail-closed 骨架，不能提升 Provider 状态。
