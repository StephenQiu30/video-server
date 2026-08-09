# 上线能力与 GitHub 开源整合调研

- 调研日期：2026-08-08
- 状态：Completed
- 范围：当前 `video-server` 仓库、GitHub 公开仓库、现有自动化门禁
- 结论：保留自有安全编排和领域层，按边界引入成熟组件；当前尚不满足公网生产上线条件。

> 2026-08-10 边界更新：Cookie 不再一刀切排除；005 将其定义为默认关闭、Provider allowlist、与出口绑定的受控会话。普通媒体请求、消息、日志和 Generic 仍不得携带 Cookie，私有/DRM 边界不变。

## 执行摘要

当前项目已经完成了一个结构扎实的下载与 AI 分析 MVP，不应改造成另一套一体化下载站，也不应重新实现 extractor、FFmpeg、队列或对象存储。推荐路线仍是“成熟底层工具 + 自有安全编排与产品领域层”。

但“核心闭环可运行”不等于“可直接公网发布”。本次源码核查发现，真正的 P0 不是继续堆平台适配，而是收紧运行时边界、补齐滥用防护和配额、真正执行制品清理、建立可升级数据库与备份恢复、加入可观测性和故障演练，并恢复当前已经变红的质量门禁。

产品功能方面，音频下载、字幕、受限批量/播放列表、任务删除与重试、Provider 状态页和实时任务事件是 P1；频道订阅、浏览器扩展、通知/Webhook、账户与计费属于 P2 或商业化决策，不应阻塞首个安全公网版本。

## 调研方法

1. 阅读根 README、Security、AGENTS、现有 Design/PRD/Plan/Acceptance 与研究文档。
2. 核对 HTTP 路由、领域模型、Runner、Worker、数据库 schema、Compose、Dockerfile、CI 与前端交互。
3. 使用 GitHub 仓库检索和仓库元数据接口确认候选项目仍为公开、未归档仓库，并阅读其 README、许可证和安全/部署说明。
4. 在本地执行当前后端与前端质量命令，区分历史验收证据与 2026-08-08 的真实结果。

本调研不复制候选项目代码，不修改业务实现，也不把 GitHub stars 当作安全性或可维护性的替代证据。

## 当前真实能力基线

| 能力域 | 已存在的实现 | 判断 |
| --- | --- | --- |
| 下载闭环 | URL inspect、语义格式、异步任务、取消、重试、进度、短时下载 URL | 已实现 MVP 主链路 |
| 媒体处理 | 隔离 Runner、固定 yt-dlp 参数、FFmpeg/ffprobe、SHA-256、大小/时长/工作区限制 | 代码边界较完整 |
| 异步可靠性 | PostgreSQL 事实源、transactional outbox、RabbitMQ、lease/heartbeat、stale recovery、幂等键 | 已实现 |
| 存储 | MinIO 私有 bucket、短时预签名 URL、artifact expiry 字段 | 只完成“不可再签发”，未完成物理回收 |
| 用户隔离 | HttpOnly/Secure/SameSite 匿名签名 Cookie、`owner_hash` 资源隔离 | 适合匿名 MVP，不等于账户体系 |
| 多平台 | Provider Registry、Generic fallback、独立出口配置、MediaTrack 插件 | 目录存在，但真实可用性受站点和出口影响 |
| 历史 | 当前会话分页、搜索、状态过滤、统计、详情跳转 | 已实现，真实依赖验收仍未冻结 |
| AI | 独立任务/Worker、ASR、LLM schema、evidence 校验、摘要/章节/导图 UI | 自动化完成，真实 ASR + 视频 E2E Pending |
| API 契约 | FastAPI OpenAPI、稳定 operationId、生成前端客户端、Problem Details | 已实现 |
| 交付 | Next.js 静态构建 + FastAPI 同源单镜像、Compose 本地/生产覆盖 | 可构建，不等于生产拓扑完整 |
| 测试 | 348 个后端测试、29 个前端测试；mypy 与前端全门禁通过 | 当前 Ruff 与 format 失败 |

## 已验证的上线缺口

### P0：必须在公网发布前完成

| 编号 | 缺口 | 源码证据 | 风险/后果 | 目标结果 |
| --- | --- | --- | --- | --- |
| P0-01 | Runner 的网络与 Secret 边界只停留在代码约定 | Compose 为 `media-runner` 注入整份 `.env`/`.env.prod`，所有服务共用默认网络；Runner 容器可见数据库、消息、MinIO、AI 等环境变量，也存在默认外网路径 | Runner 或媒体依赖被利用后可读取业务 Secret、横向访问内部依赖或绕过 Squid 直连 | 服务专属 env、内部/出口网络分段、Runner 仅持有 HMAC 与无凭据代理地址，网络测试证明无法直连公网和业务依赖 |
| P0-02 | 公网入口没有系统级滥用防护 | API 仅有匿名会话，没有 IP/会话/API key 限流、并发配额、每日字节/AI 成本配额、bot challenge 或可信代理策略 | 免费算力/带宽被刷、队列堆积、出口 IP 被封、AI 账单失控 | 多维限流、原子配额、`429 + Retry-After`、全局 backpressure、可选 Turnstile/API key |
| P0-03 | artifact TTL 没有物理删除执行器 | schema 有 `expires_at/deleted_at`，对象存储有 delete 方法，但没有扫描过期 artifact 并删除 MinIO 对象与元数据的生命周期 Worker | 隐私与存储成本持续累积，配置的 TTL 形成错误安全感 | 幂等 GC、analysis lock 保护、对象删除重试、孤儿对账、MinIO 生命周期兜底 |
| P0-04 | 数据库只支持空卷初始化 | 仓库明确禁止 migrations，只保留 `schema.sql` | 生产升级只能丢数据或人工改表，无法回滚和审计 | 引入 Alembic，从基线 revision 开始做前向迁移；schema 快照仅用于新环境 |
| P0-05 | 缺少备份、恢复与灾难演练 | Compose 有持久卷，但没有 PostgreSQL/MinIO/RabbitMQ 备份策略、恢复脚本或 RPO/RTO 验收 | 节点/磁盘故障后不可恢复 | 定义 RPO/RTO，完成加密备份、恢复演练和证据记录 |
| P0-06 | 缺少生产可观测性 | 无结构化日志、请求 ID、中间件指标、Provider 聚合指标、Tracing 或告警规则；Runner 关闭 access log | 无法定位错误、容量、出口或平台回归 | 脱敏 JSON 日志、Prometheus 指标、队列/Worker/Provider/存储仪表盘、告警与 runbook |
| P0-07 | 真实可靠性证据不足 | 002 的第三方矩阵与故障注入未完成；003 真实 ASR E2E Pending；004 真实依赖验收 Pending | 上线后才暴露格式漂移、重复投递、磁盘耗尽和 Provider 失败 | 固定受控 E2E、故障注入、负载/容量基线、定时 Provider canary 与状态页 |
| P0-08 | 生产入口和响应安全未冻结 | 生产 Compose 直接暴露 API 端口，没有仓库内 TLS/反向代理/安全 header/body limit 方案 | TLS、请求体、超时和代理 IP 语义依赖外部手工配置 | 明确受支持 ingress，配置 TLS、HSTS、CSP、body/header/timeouts、可信代理链 |
| P0-09 | CI/供应链门禁不完整且当前不绿 | 后端 Ruff 1 个 E501、format 3 文件失败；CI 使用 Node 22/npm 11.16，而 package/Docker 要求 Node 24/npm 11.19；无镜像/Secret/SBOM 扫描 | 合并门禁与真实构建环境漂移，依赖风险不可见 | 恢复全绿、统一工具链、依赖/镜像/Secret 扫描、SBOM、固定镜像 digest 与发布签名 |
| P0-10 | 上线治理与法律入口缺失 | Security 说明了边界，但产品内没有使用确认、隐私/保留策略、投诉/下架流程、运维值班和发布/回滚清单 | 滥用与合规请求无法处理，事故响应不可执行 | 产品内展示边界，建立隐私/条款/投诉/删除/事件响应和回滚手册 |

### P1：首个稳定版本应补齐的产品能力

| 能力 | 当前缺口 | 建议范围 |
| --- | --- | --- |
| 音频下载 | 语义计划要求视频宽高与视频 codec，UI 只有视频格式 | `audio_only` 计划，优先 M4A/Opus；MP3 作为显式转码且有 CPU/大小上限 |
| 字幕 | inspect/计划/制品模型没有字幕轨道 | 列出人工/自动字幕，支持单独下载和受控嵌入，不默认伪装 AI 转录为原字幕 |
| 批量/播放列表 | Runner 固定 `--no-playlist`，metadata 明确拒绝 playlist/multi_video | 先支持最多 N 条的受限批量父任务；禁止频道无限抓取和任意递归 |
| 多媒体帖子 | 当前模型只允许一个视频制品 | 为图片/多视频帖子返回可选条目，不静默只取第一条 |
| 用户操作 | 没有删除历史、删除制品、重新下载、失败后显式重试 | 增加幂等删除、重试、过期说明和审计事件 |
| Provider 透明度 | 页面把 extractor 目录描述成“支持”，没有实时健康状态 | 展示 `verified/degraded/access_required/unsupported`、最近验证时间和错误分类 |
| 实时任务状态 | 前端每 1.5 秒轮询下载和分析 | 增加 SSE；保留轮询作为降级路径并支持退避/抖动 |
| AI 产品闭环 | 没有真实 E2E、分析历史、导出和可选本地 ASR | 先完成真实证据；再补 JSON/Markdown 导出和 faster-whisper adapter |
| 匿名会话体验 | Cookie 到期后 owner 变化，旧历史不可恢复 | 滚动续期；是否引入账户与跨设备同步作为独立产品决策 |
| 可访问性/国际化 | UI 文案和错误主要为中文，尚无系统级 a11y/E2E | WCAG 基础检查、键盘/读屏测试、错误与状态国际化 |

### P2：有明确产品方向后再做

- 频道/播放列表订阅、定时增量下载、归档规则。
- 浏览器扩展、书签脚本、移动端 Share Sheet。
- 邮件、Apprise、Webhook 或聊天机器人通知。
- 注册用户、团队空间、API keys、计费与套餐。
- 媒体库/Plex/Jellyfin/Kodi 元数据与 RSS。
- SponsorBlock、章节切割和高级命名模板。

P2 中的未受管 Cookie、私有内容、任意 yt-dlp 参数或自定义脚本仍不进入当前产品安全边界；受控 Provider 会话按 005 独立实施和验收。

## GitHub 候选项目与整合结论

### 下载与产品参照

| 项目 | 可借鉴/复用能力 | 许可证与边界 | 决策 |
| --- | --- | --- | --- |
| [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | extractor、格式、字幕、音频、playlist、插件机制 | 仓库源码为 Unlicense，但发行物可能包含其他许可证；参数面很大 | 继续作为固定提交的 Runner 内核；只开放自有语义计划，不开放原始参数 |
| [alexta69/metube](https://github.com/alexta69/metube) | 音频、字幕、缩略图、播放列表、队列并发、订阅、清理 UX | AGPL-3.0；Cookie 与可选任意 yt-dlp override 没有本项目的业务面隔离 | 借鉴其 Cookie 文件权限/原子替换和交互，不复制代码、不直接部署为内部服务 |
| [imputnet/cobalt](https://github.com/imputnet/cobalt) | 粘贴即下载、服务能力矩阵、IP/session/API key 限流、Turnstile、防滥用文档 | AGPL-3.0；代理式交付和专用 extractor 架构不同 | 借鉴防滥用与 Provider 状态模型，不复制 API/Web 代码 |
| [kieraneglin/pinchflat](https://github.com/kieraneglin/pinchflat) | 定时订阅、自动清理、通知、Prometheus、媒体中心元数据 | AGPL-3.0；偏 YouTube 归档且允许 Cookie/自定义脚本 | 只作为 P2 归档产品参照 |

MeTube 和 cobalt 的公开文档都提醒：频繁更新 yt-dlp、限制并发、保护公网实例是服务可靠性的组成部分，不是可选运维优化。它们同时说明任意 yt-dlp options 会带来命令执行风险，这与本项目禁止参数透传的结论一致。

### 可直接引入的基础组件

| 项目 | 目标用途 | 推荐方式 | 备注 |
| --- | --- | --- | --- |
| [sqlalchemy/alembic](https://github.com/sqlalchemy/alembic) | PostgreSQL schema 版本和生产迁移 | Python 依赖 + `backend/alembic/`，以当前 schema 建基线 revision | 需要先修改仓库“禁止 migrations”的治理规则 |
| [valkey-io/valkey](https://github.com/valkey-io/valkey) + [alisaifee/limits](https://github.com/alisaifee/limits) | 分布式 IP/session/API key 限流、短期并发令牌 | 独立 Valkey 服务 + FastAPI 中间件/依赖；长期用量仍落 PostgreSQL | 限流不可只用进程内内存，否则多实例不一致 |
| [trallnag/prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator) | FastAPI RED 指标 | 只导出低基数、脱敏指标；内部 metrics 端点 | Provider、队列和 Worker 指标仍需自定义 |
| [open-telemetry/opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib) | API→DB→消息→Worker 跨进程追踪 | P1 可选；先验证所选 instrumentation 的稳定性 | 上游明确提示 contrib instrumentation 多数仍为 beta，不作为 P0 唯一诊断手段 |
| [caddyserver/caddy](https://github.com/caddyserver/caddy) | 单机/Compose ingress、TLS、安全 header、请求限制 | 作为可选受支持入口，静态前端仍由 FastAPI 同源提供 | Apache-2.0；不改变“无独立前端容器”原则 |
| [aquasecurity/trivy](https://github.com/aquasecurity/trivy) | 依赖、镜像、配置与 Secret 扫描，生成 SBOM | GitHub Actions + 发布前镜像扫描 | Apache-2.0；扫描规则与例外必须版本化 |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 可选本地 ASR | 独立 analysis adapter/worker profile | MIT；默认镜像不打包大模型，不阻塞托管 ASR |
| [markmap/markmap](https://github.com/markmap/markmap) | 思维导图渲染与导出 | 只消费中立 evidence tree | MIT；后端不可持久化 markmap 私有格式 |

### 明确不做的整合

1. 不 fork MeTube/cobalt/Pinchflat 来替换当前服务。
2. 不复制 AGPL 项目源码到 MIT 仓库；若未来改变策略，必须先做正式许可证评估。
3. 不接公共解析 API、公共 Cloudflare Worker 或用户不可审计的中转服务。
4. 不在普通媒体 API 上传 Cookie、不托管未受管的全浏览器 Cookie；005 的受控 Provider 会话使用独立 Vault/Secret。私有/DRM 内容和签名绕过仍不允许。
5. 不开放任意 yt-dlp 参数、输出模板、外部 downloader、`--exec` 或自定义脚本。
6. 不用 Provider 列表或 yt-dlp supported-sites 数量宣称可用性；只能用真实 canary 结果。

## 推荐目标架构

```text
Internet
  ↓ HTTPS / request limits / security headers
Supported Ingress
  ↓
API + static frontend
  ├─ PostgreSQL（用户、任务、配额、outbox、审计）
  ├─ Valkey（短窗口限流、并发令牌）
  ├─ RabbitMQ（下载/分析队列）
  └─ MinIO signing（不读取对象内容）

Download Worker ── DB/RabbitMQ/MinIO/HMAC ──→ Media Runner
Analysis Worker ── DB/RabbitMQ/MinIO/AI provider

Anonymous Media Runner（仅 HMAC + 工作区 + 无凭据代理地址）
  ↓ internal-only network
Egress Proxy（唯一具有外网路由的媒体组件）
  ↓
Public media providers

Credentialed Runner（005 验收后；单 Provider 短租约 + 独占 tmpfs）
  ↓ 同一 Egress Proxy / 固定 affinity
Public media providers

Lifecycle Worker ── DB/MinIO（过期删除、孤儿对账）
Canary Worker ── 受控样本/Provider 状态
Metrics/Logs ── 内部采集，不含源 URL query、transcript 或 Secret
```

## 推荐实施顺序

1. 恢复质量门禁，并统一 Node/npm/Python/uv 版本。
2. 先修 Compose Secret 和网络隔离，再做任何新 Provider 或媒体类型。
3. 引入 migrations、备份恢复和 artifact GC，建立可安全升级/可恢复的数据平面。
4. 加入滥用防护、配额、TLS ingress、安全 header 与全局 backpressure。
5. 建立结构化日志、指标、告警、Provider canary、真实 E2E 和故障注入。
6. 完成法律/隐私/投诉/事件响应/发布回滚流程后，才进入受限公网 beta。
7. beta 稳定后再实现音频、字幕、受限批量、SSE 与账户决策。

详细目标边界见 `docs/design/006-上线产品能力补全设计.md`，实施和验收分别见同编号 Plan 与 Acceptance。

## 2026-08-08 本地验证记录

| 检查 | 结果 |
| --- | --- |
| `uv run --frozen pytest -q` | 348 passed，1 个 Starlette/httpx deprecation warning |
| `uv run --frozen mypy --strict app` | 通过，188 个源码文件无问题 |
| `uv run --frozen ruff check .` | 失败：`app/runner/metadata.py` 1 个 E501 |
| `uv run --frozen ruff format --check .` | 失败：3 个文件需格式化 |
| `npm run lint` | 通过 |
| `npm run format:check` | 通过 |
| `npm test` | 10 files / 29 tests passed |
| `npm run build` | 通过，4 个静态路由产出 |
| 本地 Compose config | 使用现有 `.env` 可解析 |
| 生产 Compose config | 未执行；仓库没有本机 `.env.prod`，命令按设计拒绝缺失文件 |

该记录只用于确定当前基线，不替代真实 PostgreSQL/RabbitMQ/MinIO/Provider/浏览器 E2E。
