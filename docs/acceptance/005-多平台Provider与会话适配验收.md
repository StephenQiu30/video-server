# 005 多平台 Provider 与会话适配验收

- 状态：In Progress
- 结论：Conditional fail for production；implementation verification partially passed
- 日期：2026-08-10
- 关联 Design：`docs/design/005-多平台Provider策略设计.md`
- 关联 PRD：`docs/prd/005-多平台Provider与会话适配需求.md`
- 关联 Plan：`docs/plans/005-多平台Provider与会话适配计划.md`

## 1. 判定规则

- `[x]` 只表示已有自动化或历史真实证据；`[ ]` 表示尚未执行、证据不足或只完成了部分条件。
- Phase 1 通过需要 A–H 全部通过；Phase 2 还需要 I–J 全部通过。
- Mock yt-dlp、单次 CLI 成功或本机浏览器 Cookie 成功不能替代 production-like Runner/Worker E2E。
- metadata 成功不能替代同 context 的媒体 Range/fragment 和完整下载验证。
- 任一 Cookie 泄漏、跨 owner/Provider 使用、DRM 处理或未授权内容成功均直接判定失败。
- 外部平台波动必须记录 Provider/Profile/engine/access mode/egress/阶段与稳定码；不得只勾选状态。

## 2. A. 当前问题与治理

- [x] A1：文档、`AGENTS.md`、`SECURITY.md`、根/后端 README 对 Cookie 的表述统一为受控 Provider 会话，不再一刀切禁止。
- [x] A2：产品继续明确仅处理用户有权访问的非 DRM 内容，Cookie 不扩大 private/会员/购买权益。
- [ ] A2a：YouTube 运维账号无 Premium、频道会员、购买/租赁、private share 或个人资产；账号权益漂移会自动 disable。
- [x] A3：固定记录 yt-dlp、EJS、curl-cffi、POT Provider 和插件的 commit/version、许可证和 SBOM。
- [x] A4：当前 YouTube 故障被复现并区分为 EJS、credential、POT、egress challenge 或 provider regression，而不是泛化 502。
- [x] A5：`POST /api/inspections` 直接携带 `cookie` 仍返回 422，且错误/日志不回显该值。
- [x] A6：MeTube/cobalt/gallery-dl 参考代码没有被未经许可复制；公共解析服务没有接收用户 URL/凭据。

## 3. B. Provider Profile 与访问上下文

- [x] B1：19 个 Registry key 有版本化 Profile、capability、access mode、Cookie 域、client、attestation、出口、并发、错误和 canary 配置。
- [x] B2：registered host、extractor exists、verified、access required、unknown 和 unsupported 是不同状态。
- [ ] B3：Generic 永远没有 Cookie/POT；redirect 到已知 Provider 后重新校验和选择 context。
- [x] B4：inspection 冻结 profile、access mode、credential version、egress affinity、client、POT Provider 和 engine commit 引用。
- [x] B5：下载前 re-inspect、视频流、音频流、probe sample 与 remote probe 使用同一 credential snapshot/client/egress context；一次 download 内串行复用操作级 Cookie jar。
- [x] B5a：初次 inspection 的临时 Cookie 更新不进入 DB/消息；download 仍从原 version 重建 jar 并重新 inspect，不替换为当前 active version。
- [x] B6：人为修改 client/credential/egress/version 返回 `client_context_mismatch`，不静默回退或继续旧媒体 URL。
- [ ] B7：context 被撤销、版本不存在或 Profile disabled 时排队任务不启动。
- [x] B8：Registry 在启动期拒绝重复 Provider key/host，并为每个操作只生成一个包含原 URL、规范化 URL 和 Profile 的不可变 `ProviderRequest`。
- [x] B9：YouTube/TikTok 动态参数由各自 Profile 策略生成；inspect、正式下载与 probe sample 统一使用 `YtDlpCommandBuilder`，通用执行器没有平台 key 分支。
- [x] B10：检查重试、权益、metadata 补全和格式归一化由 `RunnerInspectionPipeline` 固定顺序；平台 stderr 使用可组合的有序 `FailureRule` 映射。

## 4. C. Secret 隔离与生命周期

- [x] C1：YouTube Cookie 源只读挂载到 credentialed Runner，API、Worker 和 anonymous Runner 不可见。
- [x] C2：Cookie 内容不在环境变量；配置只含固定路径和非 Secret version id。
- [x] C3：源文件验证普通文件、no symlink、Netscape header、≤1 MiB 和 YouTube 域 allowlist。
- [x] C4：每次 Runner 操作在独占 tmpfs 使用唯一目录 `0700` 和 Cookie jar `0600`；同一 jar 没有并发 writer。
- [x] C5：临时副本不在 Runner/Download Worker 共享 `/work`，Worker 无法读取。
- [ ] C6：成功、子进程失败、timeout、cancel、SIGTERM、workspace limit 和 Runner restart 后均无临时副本残留。
- [x] C7：并发操作的路径/inode 不同；一次 download 的后续命令能看到该 jar 的更新，且不改变只读源、其他任务或下一次操作。
- [ ] C8：DB、RabbitMQ/outbox、MinIO、API 响应、日志、trace、metrics、container env、snapshot 和 `/work` 扫描不到 Cookie、visitor data、PO Token 或 Authorization。
- [x] C9：非 YouTube 与 Generic 命令不含 `--cookies`，也无法打开 YouTube Secret。
- [x] C10：Runner 仍不能访问 DB/MQ/MinIO/Valkey、Docker socket 或绕过 egress proxy。

## 5. D. YouTube 全链路

- [ ] D1：匿名 Profile 在可用出口完成公开 canary metadata 与 Range/fragment。
- [ ] D2：受控运维会话完成 inspect → download re-inspect → stream download → remux → ffprobe → SHA。
- [ ] D3：单流和分离音视频流均携带相同 Cookie/UA/client/egress context。
- [x] D4：受会话保护的媒体 URL 在 remote probe 阶段不会因丢失 Cookie/Referer/UA 而失败。
- [ ] D5：有效 Cookie、缺失 Cookie、过期/rotated Cookie、拒绝 Cookie 和撤销 Cookie 得到稳定且不同结果。
- [x] D6：每个运维 credential subject 实际 active job 不超过 1；并发竞争不超发。
- [ ] D7：新 Secret 完成 pending canary 后才激活，旧版可回滚，rejected 版本从未服务用户任务。
- [ ] D8：Cookie 更新后旧 context 不复用格式 URL、POT 或出口 session。
- [ ] D9：账号/出口进入 challenge 时停止放大请求并进入 cooldown，不循环更换 client/账号。
- [x] D10：credentialed inspect/re-inspect 只允许明确 public/unlisted 且不依赖账号权益；private、premium、subscriber、needs_auth、unknown 和 DRM 在任何媒体字节下载前终止。
- [ ] D11：权益拒绝不会创建 stream 文件、artifact、MinIO 对象或下载记录；canary 发现账号权益漂移会 disable version。

## 6. E. POT、出口与重试

- [x] E1：POT sidecar 仅向内部的匿名 YouTube Runner 与 YouTube credentialed Runner 暴露，不发布宿主机端口；版本和许可证进入 SBOM/NOTICE。
- [ ] E2：GVS token 按允许的 client/video/session 自动生成，不在 DB/队列/日志长期持久化。
- [ ] E3：POT mint 与 inspect/download 使用同一 proxy/source/session binding。
- [ ] E4：sidecar unavailable、timeout、POT required、POT rejected、刷新一次成功/失败有不同稳定码。
- [ ] E5：Cookie failure、POT failure、EJS/signature failure、IP block、TLS fingerprint 和 rate limit 不互相误分类。
- [ ] E6：429 遵守 `Retry-After`；yt-dlp/Runner/Worker 总尝试次数不超过统一预算。
- [x] E7：凭据、DRM、权益、geo、deleted 和 unsupported 默认不重试。
- [ ] E8：POT/credential kill switch 可独立关闭并保留匿名/其他 Provider 链路。

## 7. F. 错误与前端

- [ ] F1：inspect/download 同构支持 credential、POT、egress、rate、geo、private/entitlement、DRM、schema、expiry 和 fragment 错误。
- [x] F2：download re-inspect 的 Provider 错误不再归为 `worker_lost` 或触发基础设施重试。
- [x] F3：当前“cookie uploads are not supported”文案已移除，用户看到具体、合法且不泄密的动作。
- [x] F4：公开 Problem Details 不暴露 Cookie 是否存在、账号、version、POT、出口地址、命令或临时路径。
- [ ] F5：`media_url_expired` 只用原 context 重检一次；仍失败则稳定终止。
- [x] F6：DRM、private、会员/购买无权益为终态，不提示继续上传/更换 Cookie 规避。
- [x] F7：Provider 状态页不使用静态清单或“1000+”承诺实时成功。

## 8. G. Provider Canary 与回归

- [ ] G1：Canary 使用项目自有或明确授权样本，不使用用户 URL/Cookie。
- [ ] G2：每个平台至少有 anonymous metadata + Range/fragment；启用会话的平台另有独立 auth canary。
- [ ] G3：Canary 已记录 provider、access mode、Profile/engine、egress/client 引用、stage、latency 和稳定码且不记完整 URL/Secret；capability 与 POT version 尚未进入结果合同。
- [ ] G4：最近 5 次、4 次成功、最近 2 次成功、2 次失败降级、3 次同类永久失败阻断和新平台显式批准 gate 已有确定性测试；授权目标真实性与用户内容隔离的运行证据待补。
- [x] G5：单 Provider 结果只改变该 Provider 聚合视图，不参与 API readiness；默认无目标的 Compose 服务已独立健康运行。
- [x] G6：Bilibili 公开 UGC 回归成功，命令不含 Cookie/POT。
- [x] G7：抖音公开分享页回归成功；动态签名/schema 故障不伪报 Cookie 缺失。
- [x] G8：小红书有效公开分享链回归成功；短链失效、图文笔记、原画缺失分别分类。
- [ ] G9：Facebook、Twitch 已完成当前 Profile 的 metadata + media canary；TikTok 保持 degraded，Reddit 保持 access_required，因此本组合项仍未全部通过。
- [x] G10：Pinterest 视频 Pin、微博/优酷/腾讯视频公开单视频已完成当前固定引擎 metadata + media；图片/相册/多资产继续 fail closed；AcFun、Rutube、VK Clips、Dailymotion、NicoNico 不登记且相关域名 fail closed。
- [x] G11：视频号稳定为 unsupported，Generic 不会把它提升为 supported。
- [x] G11a：快手由可信 `KuaishouPublicIE` 处理第一方公开单视频；图集和非第一方重定向 fail closed。
- [ ] G12：本地带 ContentProtection 的 fixture 稳定返回 `drm_protected`。

## 9. H. API、可观测性与供应链

- [x] H1：`GET /api/providers` 已从数据库最近结果动态聚合并保留配置 capability/access-mode；无 URL、账号、Cookie、出口地址或异常文本响应字段。
- [ ] H2：指标 labels 只含低基数 Provider/阶段/错误/version，不含 URL/job/owner/credential/异常文本。
- [ ] H3：凭据创建/激活/验证/撤销/lease 审计只记录非 Secret 元数据。
- [ ] H4：未登记许可证、未固定 version 或用户可加载的插件在 CI 被拒绝。
- [ ] H5：镜像和依赖扫描无未接受 Critical/High；发布物可追溯 Git SHA、Profile/engine/POT 版本和 SBOM digest。
- [x] H6：production-like Compose 证明 Runner pool、Secret mount、tmpfs、网络和 kill switch 符合设计。
- [x] H7：平台目录由 PostgreSQL 持久化，只有管理员可通过 CRUD API 和 `/admin/providers` 页面维护名称、排序与可见性；普通用户返回 403，自定义目录条目保持 `unsupported`，不能创建下载 Profile 或扩大域名 admission。

## 10. I. Phase 2 用户 ProviderCredential

- [ ] I1：凭据只能经认证、CSRF 防护、≤1 MiB multipart API 创建，响应永不含 Cookie 原文。
- [ ] I2：Vault 使用 KMS/envelope encryption；数据库只含 owner、Provider、version、状态、时间和密文引用。
- [ ] I3：普通 inspection 只接受 `credential_id`，原始 `cookie` 字段继续被拒绝。
- [ ] I4：owner A 引用 owner B 的 credential 返回 404，Runner/Broker 未被调用。
- [ ] I5：credential 不能跨 Provider、进入 Generic、operator pool 或另一用户任务。
- [ ] I6：Runner 通过 Broker 获得一次性短租约，API/Worker/RabbitMQ 不解密 Secret。
- [ ] I7：撤销后 60 秒内停止新 lease 并终止活跃子进程；重复撤销幂等。
- [ ] I8：Vault/Broker/KMS 停止、lease 过期、Runner crash 和 key rotation 有稳定故障与恢复测试。
- [ ] I9：备份、dump、日志、trace、事件、API snapshot 和错误报告扫描不到 Cookie 明文。
- [ ] I10：前端展示 Cookie 等同账号会话、账号风险、允许用途、最后验证和撤销；不能回读或复制原文。

## 11. J. Phase 2 多媒体引擎

- [ ] J1：领域模型支持受限 manifest 和多条目，不静默丢弃 carousel/gallery 项。
- [ ] J2：gallery-dl 在独立固定版本 Runner 运行，无任意配置、无视频 Runner Cookie、无业务 Secret。
- [ ] J3：Instagram/X/Reddit 的视频单条仍优先 yt-dlp，Engine router 不做无界 fallback。
- [ ] J4：条目数量、总大小、时长、TTL、owner 和部分失败语义通过测试。
- [ ] J5：GPL-2.0 分发、源码、NOTICE 和镜像 SBOM 义务完成评审。
- [ ] J6：现有单视频格式选择、下载性能、FFmpeg/ffprobe 和对象交付不退化。

## 12. 建议验证命令

```bash
cd backend
uv sync --frozen --dev
uv run ruff check app tests
uv run mypy app
uv run pytest

cd ../frontend
npm ci
npm run lint
npm test
npm run build

cd ..
docker compose --env-file .env -f docker-compose-env.yml config
docker compose --env-file .env -f docker-compose.yml config
docker compose --env-file .env.prod -f docker-compose-prod.yml config
```

真实 Cookie、POT 和 Provider canary 命令必须放在受限运维 runbook/CI Secret 环境，文档只记录脱敏结果，不把值写入 shell history 或验收文件。

## 13. 证据记录模板

| 日期 | 环境 | Git SHA | Provider/capability | Access mode | Profile/engine/POT | Egress ref | Stage | 结果/稳定码 | 证据位置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-10 | 本地单元/契约/集成 | 本次提交（基线 `a72b2f0`） | Profile/context/session/error/API | anonymous + operator fixtures | yt-dlp `5d6b8c8` / EJS `0.8.0` / bgutil `1.3.1` | non-secret fixture | inspect/download | backend `400 passed`；ruff lint/mypy 通过 | 本文第 12 节命令；测试报告 |
| 2026-08-10 | Compose config | 本次提交（基线 `a72b2f0`） | YouTube operator/POT | operator topology | `youtube-v2` / bgutil `1.3.1` OCI digest | Compose network ref | deploy config | 环境、业务、生产配置均通过 | `docker compose ... config --quiet` |
| 2026-08-10 | production-like 本地容器 | 本次提交（基线 `a72b2f0`） | YouTube operator/POT | operator fixture | `youtube-v2` / bgutil `1.3.1` OCI digest | 三个内部网络 | startup/health/boundary | Runner/POT/egress healthy；Secret ro；tmpfs `0700`；无 DB/MQ/MinIO/Valkey env 或 Docker socket；无直连公网网络 | 临时假 Cookie fixture 已删除，容器已 `down` |
| 2026-08-10 | runtime 镜像 | 本次提交（基线 `a72b2f0`） | Provider runtime | N/A | yt-dlp `2026.07.04` / bgutil plugin | N/A | build/import | runtime build 通过；SBOM/NOTICE 与插件入口存在 | image `video-server:phase1-validation`（本地） |
| 2026-08-10 | 前端本地 | 本次提交（基线 `a72b2f0`） | Provider status | authenticated | OpenAPI `listProviders` | N/A | API/UI | `81 passed`；lint/type/format/build 通过；`/providers` 静态导出 | 前端测试与 build 报告 |
| 2026-08-07 | 本地浏览器 E2E | historical | Bilibili/抖音/小红书 single video | anonymous | 当时固定 Runner | historical | metadata/media/remux/probe | 成功；范围见研究记录 | `docs/research/001-GitHub开源方案调研.md` |
| 2026-08-12 | 本地后端 | 本次提交 | Provider 范围收缩 | anonymous / 默认无目标 | yt-dlp `5d6b8c8` | non-secret default | Registry/API/Runner | 五个平台从 API 移除；相关域名不落入 Generic，稳定返回 `provider_unsupported` | `docs/acceptance/017-其他短视频平台分阶段接入验收.md` |
| 2026-08-12 | 本地全栈与浏览器 | 本次提交 | 管理员平台目录 | admin catalog / public status projection | OpenAPI `list/create/update/deleteProviderCatalogEntry` | N/A | API/UI/schema | 后端 `519 passed, 1 skipped`；前端 `107 passed`、lint/format/build 通过；Compose 开发/生产配置通过；1440px/390px 浏览器复核无问题 | `/admin/providers`、浏览器 QA 截图与本次门禁输出 |
| 2026-08-12 | 本地固定引擎/Compose Runner | 本次提交 | Facebook/Twitch/Pinterest/微博/优酷/腾讯视频公开单视频或 Clip | anonymous | yt-dlp `5d6b8c8` / Provider versioned profiles | 当前本地受控出口 | metadata/media/probe/hash | 六个平台 metadata 与实际媒体通过；Facebook 最近 5 次 4 成功且最近 4 次连续成功；结果已脱敏写入 canary 表 | `docs/research/007-剩余Provider逐平台验证调研.md` |
| 2026-08-12 | 本地固定引擎/Compose Runner | 本次提交 | YouTube/TikTok/Reddit | anonymous | yt-dlp `5d6b8c8` | 当前本地受控出口 | metadata negative | YouTube bot challenge → `access_required`；Reddit account authentication → `access_required`；TikTok unexpected webpage response → `degraded` | `docs/research/007-剩余Provider逐平台验证调研.md` |
| 2026-08-26 | 本地固定引擎/Compose Runner | 本次提交（基线 `642f464`） | Provider 接入架构重构；YouTube/TikTok/X single video | anonymous | `youtube-v2` / `tiktok-web-v1` / `x:1`；yt-dlp `5d6b8c8` | 当前本地受控出口 | image build/readiness/media/remux/probe/hash | 架构专项 `99 passed`；全量 `975 passed, 1 skipped`，仅 2 项既有 Windows 失败；三平台完整媒体分别 `102382/53142/76524 ms` 成功；API/Runner healthy | `provider_canary_results` 最新三条；`scripts/restart-project.ps1` |
| Pending | production-like | Pending | YouTube public + rights-negative | operator + POT | Pending | Pending | full Worker/Runner/MinIO | 未执行：无批准的专用 Cookie/授权 canary | `docs/operations/002-YouTube受控会话运行手册.md` |

## 14. 当前结论

截至 2026-08-12，Phase 1 已提供可配置的 YouTube 运维 Cookie/POT 路径，以及持久化 Provider 探针、定时执行器、阈值/恢复迟滞和动态 API 聚合。Facebook、Twitch、Pinterest 视频 Pin、微博、优酷和腾讯视频的当前匿名公开单视频/Clip Profile 已完成 metadata 与真实媒体证据；YouTube、Reddit 保持 `access_required`，TikTok 保持 `degraded`。验收结论仍为 **production conditional fail**：A2a、B3/B7、C6/C8、YouTube 真实 D1–D3/D5/D7–D9/D11、POT/出口 E2–E6/E8、授权 canary G1–G4/G9/G12、低基数指标/供应链 H2–H5 与完整视频 Agent E2E gate 均缺完整证据或尚未实现。不得把 YouTube 标记为 `verified`，也不得启用生产运维会话。

Phase 2 的 I–J 全部保持 Pending；本轮没有实现用户 Cookie 上传/Vault/Broker 或 gallery-dl。下一验收批次必须使用无额外权益的专用账号与授权样本，按 runbook 完成真实 Worker/Runner/MinIO E2E、全系统泄漏扫描、sidecar/出口绑定、轮换/撤销、账号权益漂移和故障注入。
