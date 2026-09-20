# BACKLOG — 视频解析与平台支持 可维护性/可用性 修复

- 来源评审：`docs/design/038-视频解析与平台支持可维护性与可用性评审.md`
- 状态：待排期；需求与计划随 038 结论同步，实施前按当前代码复核行号
- 维护约定：本文件是 038 修复的**活的工作台账**；需求（PRD）与执行计划（Plan）两节逐项可追溯到 038 的结论章节与代码位置。合并完成后，纯过程条目按 AGENTS.md §文档规范 清理，结论保留在 038 与代码内。

---

## 一、PRD（需求）

> 每条需求：**背景**指向 038 结论章节，**验收标准**为可判定条件，**优先级** P0=阻断上线 / P1=高 / P2=中。

### 可维护性（先做，投入最小）

- **R1 共享安全文件模块**
  - 背景：`_no_follow` 3 份、原子写 3 份、私有目录 fstat 校验多处重复（038 §3）。
  - 需求：新增 `_secure_file` 模块，收敛 `O_NOFOLLOW` 打开、`os.replace`+fsync 原子写、私有目录 fstat（uid/nlink/mode）校验；删除重复实现。
  - 验收：`grep` 确认 `def _no_follow`、`def _atomic_write_*` 各只剩一处定义；runner 既有测试全绿。
  - 优先级：P1

- **R2 Netscape Cookie 唯一实现**
  - 背景：解析/序列化/校验拆分在 3 个文件且规则漂移（038 §3）。
  - 需求：新增 `netscape_cookie` 模块，唯一实现解析、序列化、校验、过期过滤、`\x00` 检查、域名 allowlist 匹配。
  - 验收：cookie 读写校验只经该模块；allowlist 匹配逻辑一处；相关单测通过。
  - 优先级：P1

- **R3 凭证哈希一致性**
  - 背景：`provider_session_maintainer.py:89,273` 写未加盐 sha256，与 `provider_sessions.py:158` 的 HMAC 不一致（038 §3）。
  - 需求：统一为 HMAC（带密钥）派生凭证标识，消除未加盐哈希。
  - 验收：`state.json` 不再含未加盐 sha256；跨进程标识仍稳定可对账。
  - 优先级：P1

### 错误语义与重试/冷却（正确性）

- **R4 错误状态码分层**
  - 背景：`verification.py` 全部 502 与 `gallery.py:86` 422 冲突（038 §2-4）。
  - 需求：「产物非法/内容拒绝」统一 4xx，「基础设施/上游临时故障」保留 5xx；时长超限归为内容拒绝。
  - 验收：同一错误码不再同时承载 4xx/5xx 语义；前端错误提示可区分「链接不可用」与「服务繁忙」。
  - 优先级：P1

- **R5 失败分类全阶段覆盖**
  - 背景：`classify_provider_failure` 仅 `failure_context is not None` 时生效（038 §4）。
  - 需求：probe/remux/public_asset 阶段也携带 `failure_context`，使 provider 限流/封禁在全部子进程调用中被正确分类。
  - 验收：构造任一 probe 失败，产物落库稳定错误码而非通用 502。
  - 优先级：P1

- **R6 跨层冷却预算 + 退避/滞回 + 原因落库**
  - 背景：冷却固定 `DEFAULT_COOLDOWN`、`reason_code` 硬编码、`finish()` 不写 reason（038 §2-6）。
  - 需求：以 `(provider, egress_affinity, error_class)` 为 key 的单一冷却状态；遵守 `Retry-After`；指数退避 + jitter + 连续 N 次成功才清零的滞回；`block()/finish()` 落库 `reason_code` 与稳定错误码。
  - 验收：冷却可追溯原因；恢复需连续成功；不再「冷却→探测→解禁→再失败」抖动。
  - 优先级：P1

- **R7 删除 canary 错误码有损折叠**
  - 背景：`_RUNNER_ERROR_ALIASES` + `.get(code, "runner_failed")` 压平根因（038 §2-5）。
  - 需求：保留 `provider_errors.py` 细粒度稳定错误码；`canary_internal_error` 仅表示探测代码自身 bug，不落为平台失败证据。
  - 验收：canary 证据可区分验证码/POT 挂/凭证过期三类根因。
  - 优先级：P2

- **R8 下载队列重试可观测 + DLX 确认**
  - 背景：消费者恰好重试一次、`declare_queue(passive=True)`，DLX 绑定在外部拓扑（038 §2-1）。
  - 需求：确认 `download` 队列绑定 DLX 且 `dlq` 重放与 sweeper 三层恢复不重复计数；重试预算集中为可观测状态。
  - 验收：二次失败消息进入 DLQ 而非静默丢失；重放不重复执行幂等任务。
  - 优先级：P1

### 高可用（HA 提升）

- **R9 分布式凭证租约协调器**
  - 背景：operator 会话当前单副本 + 并发 1，是 SPOF（038 §5-1）。
  - 需求：Redis `SET NX + TTL + 心跳续租` 实现跨副本凭证租约；同一 `{provider}:{credential_version}` 同一时刻仅一个持有者；到期自动释放。
  - 验收：两副本并发请求同一凭证仅一个获租约；持有者崩溃后租约到期被接管。
  - 优先级：P0（消除 SPOF）/ P2（若短期接受单点则先文档化 + 告警）

- **R10 孤儿 workspace 文件系统 GC**
  - 背景：sweeper 只做 DB 三层恢复，无文件系统扫描（038 §2-2）。
  - 需求：年龄基回收 `{task_id}-*` 目录（超阈值且无活跃任务），info_json 复用有明确生命周期。
  - 验收：硬崩溃遗留目录在阈值后被回收；活跃任务目录不被误删。
  - 优先级：P2

- **R11 会话就绪与失效检测补全**
  - 背景：`is_ready()` 只查第一个 provider、`assert` 抛 500（038 §2-3）。
  - 需求：按 provider 校验；operator 未配 cookie 源返回受控 4xx；区分 `credential_expired` 与 `provider_link_unavailable`。
  - 验收：多 provider 场景会话失效可被 ready 感知；异常路径不再 500。
  - 优先级：P2

- **R12 状态证据对称（负向信号）**
  - 背景：证据只投影 `succeeded`，平台回归不立即可见（038 §2-7）。
  - 需求：纳入近期失败证据（带稳定错误码 + `context_generation_id` 过滤），不让个别链接失效误判为平台故障。
  - 验收：平台回归秒级反映到状态；单链接失效不污染平台状态。
  - 优先级：P2

- **R13 权益漂移自动停用**
  - 背景：缺「漂移即停用 credential version」安全网（038 §5-3）。
  - 需求：inspect attestation 检测账号权益与基线不一致即 disable 对应 `credential_version`。
  - 验收：账号意外获得会员/权限后，对应版本被停用而非 fail-open。
  - 优先级：P1

---

## 二、Plan（执行计划）

> 按 038 §6 五阶段；任务间 `→` 表依赖；每项验证对应 AGENTS.md §实现与验证 的最小充分检查。提交 scope 用后端稳定模块名（`runner` / `worker` / `canary` / `docs`）。

### P1 共享安全模块 + 凭证哈希一致性（对应 R1–R3）

- [ ] P1.1 新建 `app/workers/runner/_secure_file.py`：`_no_follow`、原子写、私有目录校验；替换 `provider_cookie_sync.py:275`、`provider_session_files.py:116`、`provider_cookie_queue.py:237` 的 `_no_follow` 与 `_atomic_write_*` 三处。
  - 依赖：无。验证：`ruff`/`mypy`/`pytest` + `grep` 确认单一定义。
- [ ] P1.2 新建 `app/workers/runner/netscape_cookie.py`：统一解析/序列化/校验/过期/`\x00`/allowlist；替换 `provider_cookie_export`、`provider_cookie_file`、`provider_session_files._validate_netscape_cookie`。
  - 依赖：P1.1。验证：cookie 相关单测全绿；allowlist 匹配收敛一处。
- [ ] P1.3 `provider_session_maintainer.py:89,273` 改 HMAC 派生，复用 `provider_sessions.py:158` 的密钥来源。
  - 依赖：P1.1。验证：状态文件哈希可跨进程稳定对账；无未加盐哈希残留。
- [ ] P1.4 收敛 `provider_cookie_*` / `provider_session_*` 职责后删除空文件与转发层，同步 PROJECT.md 目录归属（如新增模块位置）。
  - 依赖：P1.1–P1.3。验证：架构边界测试 `test_dependency_boundaries.py` 全绿。

### P2 错误语义 + 冷却预算（对应 R4–R8）

- [x] P2.1 `verification.py`/`gallery.py`/`collection.py` 产物非法统一 4xx，基础设施失败保留 5xx。
  - 依赖：无。验证：新增「时长超限→4xx」「无流→4xx」「上游 5xx 透传」回归测试。
- [x] P2.2 `commands.py` probe/remux/public_asset 构造命令时补传 `failure_context`，使 `classify_provider_failure` 全阶段生效。
  - 依赖：无。验证：probe 失败落库稳定错误码。
- [x] P2.3 冷却：`route_cooldowns.py` 增加指数退避 + jitter + 滞回；`block()/finish()` 落库 `reason_code` + 稳定错误码。
  - 依赖：无。验证：冷却可追溯；恢复需连续成功。
- [x] P2.4 删除 `canary/service.py` `_RUNNER_ERROR_ALIASES` 折叠，`canary_internal_error` 仅限探测自身 bug。
  - 依赖：P2.2。验证：canary 证据区分验证码/POT/凭证三类。
- [ ] P2.5 确认 `download` 队列 DLX 绑定；`dlq` 重放与 `sweeper` 三层恢复去重计数；重试预算可观测。
  - 依赖：无。验证：消息二次失败进入 DLQ；幂等重放不重复执行。

### P3 分布式凭证租约（对应 R9）

- [ ] P3.1 设计租约数据模型与 Redis key 规范（`{provider}:{credential_version}` + TTL + 心跳）。
  - 依赖：无。验证：方案评审通过（可选）。
- [ ] P3.2 实现租约协调器 `app/workers/runner/`（或 `integrations/`），接入 operator runner 下载前 acquire / 完成 release / 心跳续租。
  - 依赖：P3.1。验证：两副本并发仅一个获租约；崩溃后到期接管（集成测试）。
- [ ] P3.3 若短期接受单点：在 038 §5 与运行手册显式标注「operator 会话 = 单副本 SPOF」并加监控告警。
  - 依赖：P3.1。验证：文档 + 告警落地。

### P4 孤儿 GC + 会话检测（对应 R10–R11）

- [ ] P4.1 `download/sweeper.py` 增加 `runner_workspace_root` 年龄基 GC，回收无活跃任务的 `{task_id}-*`。
  - 依赖：无。验证：阈值后回收；活跃任务目录保留。
- [ ] P4.2 `provider_sessions.py is_ready()` 改按 provider 校验；`assert` 改受控 4xx。
  - 依赖：无。验证：多 provider 失效可感知；异常不再 500。
- [ ] P4.3 确认浏览器会话「Cookie 轮换失败」归 `credential_expired` 而非 `provider_link_unavailable`。
  - 依赖：P2.2。验证：构造轮换失败落库正确错误码。

### P5 状态证据对称 + 权益漂移（对应 R12–R13）

- [ ] P5.1 `status_evidence.py` 纳入失败证据（稳定错误码 + `context_generation_id` 过滤）。
  - 依赖：P2.4。验证：平台回归秒级可见；单链接失效不污染状态。
- [ ] P5.2 落实 inspect attestation 权益漂移 → disable `credential_version`。
  - 依赖：无。验证：漂移后对应版本停用，不 fail-open。

---

## 三、可追溯性

| 需求 | 038 结论 | Plan 任务 |
| --- | --- | --- |
| R1–R3 | §3、§6.1 | P1.1–P1.4 |
| R4 | §2-4 | P2.1 |
| R5 | §4 | P2.2 |
| R6 | §2-6 | P2.3 |
| R7 | §2-5 | P2.4 |
| R8 | §2-1 | P2.5 |
| R9 | §5-1、§6.3 | P3.1–P3.3 |
| R10 | §2-2 | P4.1 |
| R11 | §2-3 | P4.2–P4.3 |
| R12 | §2-7 | P5.1 |
| R13 | §5-3 | P5.2 |

- 建议排期：P1 → P2（可并行，P2.5 独立）→ P5.2（安全网，尽早）→ P3 → P4 → P5.1。
- 每项完成后按 AGENTS.md §Git 与任务交付 提交：`refactor(runner): <中文描述>` / `fix(worker): ...` / `feat(runner): ...`，附回归证据，未验收不勾选。
