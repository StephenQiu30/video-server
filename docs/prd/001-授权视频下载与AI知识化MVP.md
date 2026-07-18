---
layer: PRD
status: accepted
version: "2.0.0"
canonical_path: docs/prd/001-授权视频下载与AI知识化MVP.md
purpose: "冻结 MVP 用户价值、需求编号、范围和成功指标"
inputs:
  - "docs/design/001-授权视频下载与AI知识化产品设计.md"
  - "docs/design/002-服务端技术与数据架构设计.md"
  - "docs/design/003-API与任务状态契约设计.md"
  - "docs/design/004-Plan001来源解析安全与持久化设计.md"
  - "docs/design/005-邮箱身份与持久化基础设施设计.md"
outputs:
  - "docs/plans/000-邮箱身份与持久化基础设施计划.md"
  - "docs/plans/001-URL异步解析与清晰度目录计划.md"
  - "docs/plans/002-清晰度下载与媒体交付计划.md"
  - "docs/plans/003-AI转录总结与思维导图计划.md"
  - "docs/plans/004-PDF导出与生命周期计划.md"
  - "docs/acceptance/000-MVP验收总览.md"
  - "docs/acceptance/002-邮箱身份与持久化基础设施验收.md"
---

# 授权视频下载与 AI 知识化 MVP

## 1. 问题与价值

用户面对已获授权的视频时，通常要分别处理来源解析、规格选择、下载、转写、总结、思维导图和 PDF，过程割裂且难以验证。MVP 提供统一入口和可追溯的异步工作流，并把合规、安全、时间证据和数据删除作为产品能力。

## 2. MVP 成功定义

- 授权测试来源解析成功率 100%，受支持线上样本目标不低于 95%。
- 清晰度目录出现时间 p95 不超过 8 秒。
- 负向安全与政策数据集阻断率 100%，不得开始媒体下载。
- 受控网络下载成功率不低于 99%，线上样本目标不低于 95%。
- 最终分辨率、音轨、容器与选择一致率 100%。
- AI 结构化 Schema 通过率 100%，严重事实幻觉为 0。
- 关键事实至少 95% 关联时间证据。
- PDF 基准集生成成功率 100%，线上目标不低于 99%。

## 3. P0 需求

| ID | 需求 | 验收入口 |
| --- | --- | --- |
| `REQ-POL-001` | 用户必须确认版本化权利声明；保存文案 hash/locale/time，平台政策仍可独立阻断 | `AC-POL-001` |
| `REQ-POL-002` | 来源由签名 dossier 准入，可导入/撤销/过期并同步 egress ACL；至少一个 production canary | `AC-POL-002` |
| `REQ-AUTH-001` | 用户可用邮箱注册、验证、登录、注销与找回密码；公开响应不得泄露邮箱是否存在 | `AC-AUTH-001` |
| `REQ-AUTH-002` | 密码使用 Argon2；会话在 PostgreSQL 可撤销并使用安全 HttpOnly Cookie；预认证/已认证 mutation 使用可重新引导的签名 double-submit CSRF 与同源门禁；所有业务资源按 `users.id UUID` 隔离 | `AC-AUTH-002` |
| `REQ-DATA-001` | PostgreSQL 是用户、会话、任务、事件、outbox、资产元数据和 AI 文档的唯一业务事实 | `AC-DATA-001` |
| `REQ-REDIS-001` | Redis 只承载 Celery broker、SSE 唤醒、缓存和限流，可在数据全失后由 PostgreSQL/outbox 重建 | `AC-REDIS-001` |
| `REQ-MAIL-001` | 注册 commit→callback 间隙由未验证用户扫描恢复；重发验证/找回密码先持久化 PostgreSQL delivery intent，再由幂等 callback/reconciler 建 mail outbox，经 aiosmtplib/SMTP 异步有限重试；不得虚构跨 adapter 原子事务或破坏 generic response 防枚举 | `AC-MAIL-001` |
| `REQ-OBJ-001` | MinIO 私有保存二进制对象；对象只有在 HEAD 与 SHA-256 校验后 READY，权属/状态/version/保留期在 PostgreSQL | `AC-OBJ-001` |
| `REQ-DR-001` | PostgreSQL WAL/PITR、Redis 重建、MinIO 独立备份与跨层对账必须有可复现恢复演练和明确 RPO/RTO | `AC-DR-001` |
| `REQ-CONTRACT-001` | 身份、会话、资产与错误 OpenAPI 可重复生成，并作为 video-web 实现的唯一 HTTP 事实来源 | `AC-CONTRACT-001` |
| `REQ-SRC-001` | 接受公开 HTTPS 链接并异步解析来源能力；不接受明文 HTTP 或协议降级 | `AC-SRC-001` |
| `REQ-SRC-002` | 展示来源真实存在的规格、音频状态和预计大小 | `AC-SRC-002` |
| `REQ-SRC-003` | 只暴露不透明格式键，不泄露真实媒体 URL | `AC-SRC-003` |
| `REQ-SEC-001` | 阻断私网、metadata、危险协议、重定向和 DNS rebinding | `AC-SEC-001` |
| `REQ-DL-001` | 只有 current signed policy 明确允许 `download` 且重新确认当前权利声明后，才可选择规格异步下载并查看进度、取消和有限重试 | `AC-DL-001` |
| `REQ-DL-002` | 必要时合并音视频并校验最终媒体规格 | `AC-DL-002` |
| `REQ-ASSET-001` | 大文件通过短期签名地址交付，默认 24 小时内删除原始媒体 | `AC-ASSET-001` |
| `REQ-UP-001` | 无法合规下载时允许上传合法持有的本地文件做 AI 分析 | `AC-UP-001` |
| `REQ-AI-001` | 中英文语音或字幕转写，保留时间范围和低置信度 | `AC-AI-001` |
| `REQ-AI-002` | 生成一句话摘要、核心观点、章节、术语和行动项 | `AC-AI-002` |
| `REQ-AI-003` | 生成二至四层思维导图 JSON/SVG，并关联证据 | `AC-AI-003` |
| `REQ-PDF-001` | 用户可编辑结构化结果并导出含可选择文本的 PDF | `AC-PDF-001` |
| `REQ-PRI-001` | AI 同意独立，结果默认私有，并支持立即删除与自动过期 | `AC-PRI-001` |
| `REQ-OBS-001` | 每个失败都有稳定错误码、终态、可操作提示和事件证据 | `AC-OBS-001` |
| `REQ-API-001` | 创建接口幂等；Job 状态只以 PostgreSQL 为真相 | `AC-API-001` |

## 4. P1 需求

- 批量任务与播放列表。
- 官方 OAuth 来源与用户自有平台资产。
- 字幕翻译、多语言 PDF 和知识模板。
- 团队空间、公开分享、审阅和协同版本历史。
- 完全本地 AI 与私有部署模式。
- 关键帧与多模态视觉总结。

P1 不能在 P0 Plan 中以“顺手实现”方式进入范围。

## 5. 明确非目标

- DRM、EME、密钥或加密清单绕过。
- 登录墙、付费墙、地区限制、反机器人或创作者禁用下载的绕过。
- 导入 Cookie、账号密码或浏览器会话。
- YouTube 下载、缓存、音视频分离或离线播放，除非获得书面批准。
- 去水印、移除署名、权利管理信息或内容再分发。
- 直播录制、永久媒体库和无限保留。
- MVP 阶段宣称理解全部画面。

## 6. 用户故事

1. 作为内容创作者，我粘贴有权处理的链接后，先看到可探测的真实规格；只有下载阶段再次通过 current policy/rights 检查时才看到可下载结论。
2. 作为编辑，我能看到每个规格是否含音频、是否需合并和预计大小。
3. 作为学习者，我能下载文件并获得带时间证据的摘要和章节。
4. 作为知识工作者，我能编辑 AI 结果并导出结构清晰的 PDF。
5. 作为隐私敏感用户，我能拒绝第三方 AI、删除数据并看到保留期限。
6. 作为受限来源用户，我得到明确阻断原因和合法替代路径，而不是隐式失败。

## 7. 约束与限额

初始默认值由配置提供并可在后续 Plan 调整：单视频时长不超过 120 分钟；单任务下载不超过 5 GiB；每用户并发重任务不超过 2；原始媒体 24 小时、未保存结果 7 天、显式保存输出至用户删除、备份删除不超过 30 天、签名下载地址 15 分钟过期；生产默认 RPO≤5 分钟、RTO≤2 小时。MVP 支持邮箱多用户私有空间，不包含团队、公开分享或跨用户资源复用。

## 8. 数据与隐私

不得在日志记录完整 URL 查询参数、Cookie、Authorization、源站签名 URL、转写正文或 AI 原始响应。AI 调用必须记录供应商、模型、提示词版本、区域与数据控制配置，但不记录用户内容。

下载同意和 AI 第三方处理同意必须分开。未同意 AI 时仍可只下载；无法下载时可只上传本地文件分析。Plan 001 的权利 statement catalog append-only；来源明细 7 天清除，policy/attestation 最小审计不包含 URL 或标题并在 30 天清除。

邮箱规范化值、密码散列、一次性 token 摘要、delivery intent、数据库会话和身份审计只保存在 PostgreSQL；待投递 token material 只能按 Design 005 冻结的 cryptography AES-256-GCM envelope 在 mail outbox 中加密、限时存在。密码重置必须在一个 PostgreSQL command transaction 中同时更新 Argon2id hash、撤销全部数据库会话、消费 current intent 并写审计。Redis 不保存权威 session 或 mail intent。MinIO 只保存私有二进制，公开 API 不返回永久 object key。SMTP 是投递通道，邮件投递状态与 retry outbox 保存在 PostgreSQL。

## 9. 依赖顺序

`Plan 000 → Plan 001 → Plan 002 → Plan 003 → Plan 004 → Plan 005`。每个 Plan 的 Acceptance 全部 `passed` 后才可解锁下一个；Plan 001 已完成的局部 PostgreSQL Green 在 Plan 000 完成前不能升级为全局通过。

## 10. 风险

- 平台政策和解析器变化可能导致能力回退。
- 上游 URL 可能形成 SSRF、重定向和资源耗尽攻击面。
- AI 供应商可能限流、失败或产生不忠实总结。
- 中文字体、SVG 和分页可能导致 PDF 兼容问题。
- 大文件、长音频和并发会放大存储、网络和模型成本。
- SMTP 延迟或失败会阻断验证/找回，因此必须使用 PostgreSQL mail outbox、有限重试与 generic response。
- MinIO Community 上游归档会放大安全补丁与运维风险；生产必须明确维护发行版/责任并通过备份恢复验收。

## 11. 变更记录

| 版本 | 日期 | 变更说明 |
| --- | --- | --- |
| 2.0.0 | 2026-07-18 | 独立复审通过；以邮箱 UUID 用户、数据库 Cookie 会话、PG/Redis/MinIO/SMTP 和灾备 P0 替换 installation 身份基线 |
| 1.0.1 | 2026-07-18 | 将 Plan 001 输入冻结为公开 HTTPS，拒绝明文 HTTP 与协议降级 |
| 1.0.0 | 2026-07-18 | 独立复审通过，冻结 MVP 需求与指标基线 |
| 0.3.0 | 2026-07-18 | 增加签名来源生命周期、版本化权利声明和清理审计 |
| 0.2.0 | 2026-07-18 | 增加安装级主体、owner 隔离与 Plan 001 部署边界 |
| 0.1.0 | 2026-07-18 | 初始化 P0/P1、需求编号、指标和边界 |
