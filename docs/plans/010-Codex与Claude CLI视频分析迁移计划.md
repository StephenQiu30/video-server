# 010 Codex 与 Claude CLI 视频分析迁移计划

- 状态：In Progress（Codex 已验收，Claude Windows 沙箱与真实视觉 E2E 待完成）
- 日期：2026-08-10
- 关联 Design：`docs/design/010-Codex与Claude CLI视频分析设计.md`
- 关联 PRD：`docs/prd/010-Codex与Claude CLI视频分析需求.md`
- 当前实现：010 已替换旧 AI 链路并成为运行时事实
- 验收结果：Codex 通过；Claude 2.1.232 于 2026-08-14 因当前 Windows 会话的沙箱 feature gate 未启用而拒绝启动，尚未进入视觉推理

## 1. 实施原则

- 这是旧 AI 链路的替换，不是新增第三、第四个 Provider；切换后删除 OpenAI ASR、DeepSeek、Ollama 和 LangChain。
- 先固定业务 Schema 和安全边界，再写 Provider argv；不让 CLI wrapper 反向污染领域模型。
- 应用不实现镜头检测算法，FFmpeg 只做受限解码，由 AI 决定取样细化和语义结论。
- 两个 Provider 独立实现、共享端口与验收；不得复制整套任务编排。
- 自动化使用 fake CLI，真实账户 E2E 只作为受控人工门禁。
- 每个阶段是可独立验证和提交的小任务；不得把所有迁移堆进一个不可审查提交。
- 旧 003 当前文档已删除，历史只通过 Git 查阅；Acceptance 如实保留 Claude 未通过项。

## 2. Phase 0：冻结基线并验证两套 CLI

### 工作项

1. 记录当前后端、前端、Compose 和 003 自动化门禁，确保迁移缺陷可以与旧基线区分。
2. 添加只读 preflight 规格：
   - `command -v`/realpath、可执行权限和版本解析。
   - Codex `codex login status` 必须为 ChatGPT 管理登录。
   - Claude `claude auth status --json` 必须为 first-party OAuth。
   - FFmpeg/FFprobe 可执行且版本可解析。
3. 在临时无敏感数据目录做配置/capability smoke，不分析真实视频、不声称已验证模型工具的全部越界行为：
   - Codex 支持 `exec`、`--ephemeral`、`--ignore-user-config`、`--output-schema` 和 workspace sandbox。
   - Claude 支持 `-p`、`--safe-mode`、`--json-schema`、`--tools`、`--no-session-persistence` 和强制 sandbox。
4. 明确支持版本范围或最小能力集合；版本只是快速诊断，最终以 capability test 为准。
5. 记录数据边界：本机负责解码和编排，代理查看的帧会发往 OpenAI/Anthropic 云端；真实文件/网络阻断进入部署前安全 E2E。

### 验证

- preflight 不触发模型推理、不打印账户 email/组织/Token。
- API Key 环境变量存在或 CLI 处于 API Key 登录时稳定失败。
- capability 缺失时 Worker 在连接队列前退出。

## 3. Phase 1：定义视频分析领域模型与公共端口

### 工作项

1. 在 `backend/app/domain/analysis/` 将结果切换为唯一当前态视觉结果契约：
   - 新增/重写 `VisualAnalysisResult`、`Shot`、`Highlight`、`VisualAsset` 和限制对象。
   - 将 evidence 从 transcript segment 改为 shot id。
   - 实现严格解析、连续时间分区、引用、媒体元数据和总大小校验。
   - 由服务端派生 media、shot count、高光时间、资产首次出现时间和 Shot→Asset 反向索引，不要求模型重复返回。
   - 删除未校准的模型 confidence；camera motion 使用排他单枚举。
2. 在 `backend/app/application/analysis_execution/ports.py`：
   - 删除 `AudioPreprocessor`、`Transcriber`、文本 `Analyzer`。
   - 增加 `VideoAnalysisRequest` 与 `VideoAnalyzer`。
3. 重写 `AnalysisExecution`：
   - `materialize → analyze → validate → publish`。
   - 阶段改为 `preparing → analyzing → validating`。
   - 保持 claim、lease、heartbeat、cancel、retry 和 cleanup 语义。
4. 删除公共视觉结果的 Schema 版本字段，并用仓库内 Skill 提供多种分析场景。
5. 删除不再使用的 `Transcript`、`TranscriptSegment`、`AudioChunk` 领域/应用类型；不保留兼容字段。

### 验证

- 领域单元测试覆盖合法最小/最大结果。
- 未知字段、重复 ID、首镜不从 0 开始、分镜间隙/重叠、末镜未到权威时长、时间越界和悬空高光/资产引用全部失败。
- `domain` 不导入 Path 以外的基础设施细节、CLI 包或 Pydantic/FastAPI。

## 4. Phase 2：实现隔离任务工作区和进程监管

### 工作项

1. 重构 `backend/app/infrastructure/analysis_media/`：
   - 删除音频提取与 25 MB ASR 分块逻辑。
   - 建立固定的任务目录、输入 materialization、Prompt/Schema/policy 复制和清理。
   - 视频使用固定 `input/video.bin`，不保留外部文件名或远程 URL。
2. 扩展 `backend/app/runner/process.py`：
   - 支持 `stdin: bytes | None`，Prompt 不进入 argv 或 shell。
   - stdout、stderr 使用独立字节上限和截断标记。
   - 允许 Provider 结果写受限文件，同时验证 regular file、realpath、owner 和最大字节数。
   - 继续使用独立进程组；取消/超时先 TERM 后 KILL。
3. 增加运行期 `WorkspaceQuotaMonitor`：
   - 限制总字节、文件数、图片数和单图大小。
   - 防止符号链接、硬链接、FIFO、socket、设备文件和越界 realpath。
   - 超限时取消 CLI 并稳定映射 `analysis_resource_limit`。
4. 构造最小子进程环境：
   - 仅保留受控 PATH、真实 HOME、任务 TMPDIR、locale 和 CLI 必要配置。
   - 删除 DB、RabbitMQ、MinIO、runner、签名、云凭据和所有 Key/Token。
5. 输入 artifact 在任务期间保持 retention lock；每个 attempt 独立目录并最终清理。

### 验证

- 单元测试覆盖 stdin、stdout/stderr 截断、timeout、cancel、TERM→KILL 和子孙进程清理。
- 集成测试覆盖路径穿越、符号链接交换、超大输出、磁盘越限和并行相邻任务读取。
- 清理失败不能覆盖任务原始错误，但必须进入受限告警。

## 5. Phase 3：实现 Codex CLI 适配器

### 目标文件

```text
backend/app/infrastructure/ai_cli/
├── __init__.py
├── codex.py
├── config.py
├── errors.py
├── preflight.py
├── prompt.py
└── schema.py
```

具体拆分以单文件职责和 200 行门禁为准，不为目录对称创建空层。

### 工作项

1. 实现 `CodexAppServerVideoAnalyzer(VideoAnalyzer)`，通过有界 stdio JSONL 客户端调用 App Server，不使用 shell。
2. 生成固定调用：

```text
codex --ask-for-approval never exec
  --cd <workspace>
  --skip-git-repo-check
  --ephemeral
  --ignore-user-config
  --ignore-rules
  --strict-config
  --sandbox workspace-write
  --model <configured>
  --output-schema <schema-file>
  --output-last-message <result-file>
  -c sandbox_workspace_write.network_access=false
  -c web_search="disabled"
  -
```

3. Prompt 通过 stdin；结果只从任务目录的受限 regular file 读取并 JSON decode。
4. 解析 CLI 非零退出、认证、限流、用量、sandbox、超时和 output-schema 失败，映射公共错误。
5. `--ignore-user-config` 后仍复用 `CODEX_HOME` 认证，但禁止传入 `OPENAI_API_KEY`、`CODEX_API_KEY` 或用户 MCP/插件配置。
6. 添加安全 capability fixture，证明 App Server permission profile 无网络、无工作区外写入且不能读取被保护目录；不得改用 full access。

### 验证

- fake Codex 精确断言 argv 顺序、stdin、cwd、环境和结果文件。
- App Server 必须回归测试 `initialize`、ephemeral thread、结构化 turn 和完成事件顺序。
- session rollout 不落盘，任务取消后无 Codex/FFmpeg 进程。
- 输出合法但 shot evidence 非法时仍由领域层拒绝。

## 6. Phase 4：实现 Claude CLI 适配器

### 工作项

1. 实现 `ClaudeCliVideoAnalyzer(VideoAnalyzer)`，解析 stdout JSON 的 `structured_output`，不得误把 stdout 根对象当业务结果。
2. 使用固定调用：

```text
claude --safe-mode -p
  --no-session-persistence
  --no-chrome
  --disable-slash-commands
  --strict-mcp-config
  --settings <generated-absolute-policy>
  --tools Bash,Read
  --permission-mode dontAsk
  --allowedTools "Read(/input/manifest.json)"
  --allowedTools "Read(/work/**)"
  --allowedTools "Bash(<resolved-ffprobe> *)"
  --allowedTools "Bash(<resolved-ffmpeg> *)"
  --model <configured>
  --max-turns <bounded>
  --output-format json
  --json-schema <inline-schema>
```

Prompt 与 Codex 一样由父进程写入 stdin，不作为 argv 暴露在进程列表中。

3. 每个任务生成 policy：
   - `sandbox.enabled=true`、`failIfUnavailable=true`。
   - `autoAllowBashIfSandboxed=false`、`allowUnsandboxedCommands=false`。
   - `allowedTools` 使用 project-root 规则只开放任务内 manifest 与生成图片，sandbox 使用 realpath 后的绝对路径 deny Home read、allow 当前 workspace read/write。
   - strict network allowlist 且 domain 为空。
4. 不使用裸 `--allowedTools Read`、`--bare`、`--dangerously-skip-permissions` 或 `--add-dir`。
5. 设 `CLAUDE_CODE_SKIP_PROMPT_HISTORY=1`，从子进程环境删除所有 Anthropic Key/Token 变量。
6. preflight 只读取 `loggedIn`、`authMethod` 和 `apiProvider`；日志不记录账号或组织。

### 验证

- fake Claude 覆盖结构化输出 wrapper、缺少 `structured_output`、无效 JSON、非零退出、max turns、用量/限流和 SIGTERM 退出。
- 主动尝试 Read Home、WebFetch、Agent、Edit、MCP、非 FFmpeg Bash 和 unsandboxed escape，全部 fail closed。
- 图片 Read 能看到任务帧；不允许看到仓库、相邻任务或认证文件。

## 7. Phase 5：接入 Worker、配置与启动检查

### 工作项

1. 在 `backend/app/core/config.py` 增加类型化 CLI 配置和上限：Provider、两个 binary/model、公共 timeout/输出/工作区/图片/并发，以及 Claude 专用 max turns。
2. 删除 `analysis_provider`、`deepseek_*`、`ollama_*`、`openai_*`、转录 timeout 和旧模型 token 配置。
3. 在 `backend/app/workers/analysis/main.py`：
   - 只装配一个 `VideoAnalyzer`。
   - preflight 全部通过后再连接 RabbitMQ。
   - 并发/prefetch 首期强制为 1。
4. 删除 `workers/analysis/providers.py` 的旧配置分支，改为清晰的 CLI adapter factory；factory 不进入 domain/application。
5. 宿主机直接运行 AI Worker：
   - 更新本地 `.env.example` 为连接本地基础设施的非 Secret AI 配置。
   - 从 Compose 移除无法复用本机登录的容器化 `worker-analysis`，或按最终运行规范明确排除；不得保留一个默认必失败或会与宿主机竞争消费的服务。
   - 同步修改 `AGENTS.md`、根/后端 README 和运行手册中“Compose 完整拓扑”的描述。
   - 增加明确的 `ANALYSIS_ENABLED` 能力开关；本地与生产默认开启，生产组合只向 loopback 发布宿主机 Worker 所需端口。没有运行受支持宿主机 Worker 时，运维必须关闭该开关，不能继续创建无人消费的任务。
6. 不把登录命令自动化到 Worker；未登录错误只给出 `codex login` 或 `claude` 登录提示。

### 验证

- 配置模型测试覆盖合法 Provider、缺失 model、越限值、CLI 不存在、未登录和 API Key 模式。
- Worker 未通过 preflight 时不 ack/requeue 任何任务。
- 本地运行说明从新环境能按文档启动，且不需要 AI Key。

## 8. Phase 6：结果持久化、API 与前端适配

### 后端

1. 更新 `backend/sql/schema.sql` 当前态：
   - analysis stage 约束删除 `transcribing` 对应 rank。
   - 增加内部 provider/model/cli/prompt/schema provenance 所需字段。
   - `analysis_results` 只保存唯一当前态的 Provider 无关 JSON。
2. 同步 ORM、repository、snapshot 和序列化，不建立迁移目录或旧 JSON 解析器。
3. 更新 `api/schemas/analyses.py` 与 OpenAPI：
   - Skill 为 `director-breakdown`，任务中保存 Skill 指令快照。
   - 结果为服务端派生的 media/shot count、高光/资产时间，以及模型提供的 shots/highlights/assets 语义。
   - 不公开 provider、model、CLI/session/account/Prompt 元数据。
4. 保持创建/查询/取消 URL、owner 404、幂等和 Problem Details 语义。

### 前端

1. API 启动后重新运行 OpenAPI 生成，禁止手改生成文件。
2. 重构 Analysis Panel：
   - 分镜总数、分镜时间轴/列表。
   - 视觉高光及理由。
   - 按类型分组的资产目录。
   - 点击内容跳到分镜开始时间。
3. 删除转录、行动项、章节、mind map 和 `transcribing` 文案/类型/测试。
4. 补齐加载、空、失败、取消、重试、移动端和键盘状态；模型文字按纯文本。

### 验证

- 后端 OpenAPI 契约和前端生成类型一致。
- API 不返回 provenance/本机路径/CLI wrapper。
- 前端单元测试覆盖新结构、时间跳转、空高光/资产和稳定错误。

## 9. Phase 7：安全、失败、取消与资源边界测试

建立单独的安全/失败矩阵：

- 视频画面出现“读取 `~/.ssh`”“访问 URL”“忽略 Schema”等 Prompt Injection。
- 容器元数据、文件名和画面文字包含 shell 元字符、路径穿越和超长文本。
- FFmpeg 试图使用 HTTP、concat、pipe、device 或任务外本地路径。
- CLI 试图使用 WebFetch、MCP、Chrome、Agent、Edit、通用 Bash 或越界 Read。
- 工作区生成过多/过大图片、FIFO、socket、符号链接和硬链接。
- CLI stdout/stderr 洪泛、半截 JSON、结果文件替换、进程树忽略 TERM。
- RabbitMQ 重投递、lease 丢失、取消与 publish result/cleanup 竞争。
- 认证过期、网络断开、429、额度耗尽、模型拒绝、Schema 重试耗尽。

每个场景必须断言稳定错误、终态、是否重试、进程清理、目录清理和日志脱敏。

## 10. Phase 8：移除旧 Provider 并收口全部事实

只有 Phase 0—7 通过后执行：

1. 删除 `backend/app/infrastructure/ai/` 中 OpenAI transcriber 与 LangChain analyzer，删除不再使用的 audio preprocessor。
2. 从 `backend/pyproject.toml` 与 lock file 删除 `openai`、`langchain-core`、`langchain-deepseek`、`langchain-ollama` 及仅旧链路使用的依赖。
3. 从代码、Compose、`.env.example`、`.env.prod.example`、测试和 README 删除所有 `OPENAI_*`、`DEEPSEEK_*`、`OLLAMA_*` 和旧 `ANALYSIS_PROVIDER`。
4. 删除 transcript/mind-map 旧测试和 fixture，以 shot evidence 测试替代；不留下“legacy”目录或 adapter。
5. 010 改为当前事实；移除或重写 003 的旧 Provider、ASR 和 transcript evidence 内容，并更新 `docs/README.md`、operations、AGENTS 与所有交叉引用，使仓库只保留一个当前方案。
6. 全库 `rg` 验证旧 Provider/Key/ASR 只允许出现在 Git 历史，不出现在当前运行文档和源码。

## 11. Phase 9：两套真实 CLI 受控视频 E2E

### Fixture

准备项目有权使用、无敏感信息的短视频，包含：

- 5 个边界清楚的硬切分镜，并记录人工起止时间。
- 至少一个明显视觉高光。
- 可辨认的人物、地点、普通物体、产品、Logo 和画面文字测试项。
- 一帧无害 Prompt Injection 文字，用于证明权限而非依赖模型服从。

### 执行

1. 配置 Codex，运行完整下载制品 → analysis job → API → UI 流程。
2. 使用新任务配置 Claude，对同一视频重复完整流程。
3. 保存脱敏证据：Provider、模型、CLI/Prompt/Schema 版本、任务 ID、耗时、聚合 usage、结果摘要和人工核对表。
4. 不保存 OAuth、账户、完整模型 stdout 或非必要原始帧。

### 通过条件

- 两套结果均无需手改即可通过领域校验。
- `shot_count` 与受控 fixture 预设硬切数一致；边界误差满足 Acceptance 记录的容差。
- 高光和资产引用有效，视觉描述与人工观察一致。
- API/前端完整显示，取消/失败不影响下载制品。

## 12. 测试与证据矩阵

| 层级 | 必测内容 | 证据 |
| --- | --- | --- |
| Domain | Schema、连续时间分区、派生字段、引用、限制 | 单元测试 |
| Application | claim、stage、lease、retry、cancel、publish、cleanup | 单元测试 |
| Process | stdin、timeout、截断、进程组、quota | 单元/集成测试 |
| Codex adapter | argv、auth、result file、错误分类 | fake CLI + capability smoke |
| Claude adapter | argv、policy、wrapper、工具/沙箱 | fake CLI + capability smoke |
| Persistence/API | current SQL、JSONB、OpenAPI、owner/幂等 | repository/API 测试 |
| Frontend | 新结果、跳转、状态、移动端/键盘 | Vitest + 浏览器检查 |
| Security | injection、越界、联网、Secret、恶意文件 | 负向集成测试 |
| Real E2E | 同一视频分别走两套真实 CLI | 脱敏人工验收记录 |

## 13. 建议提交拆分

1. `feat(backend): 定义视觉分镜分析领域契约`
2. `refactor(runner): 增强分析子进程与工作区监管`
3. `feat(worker): 接入 Codex CLI 视频分析`
4. `feat(worker): 接入 Claude CLI 视频分析`
5. `feat(api): 切换视觉分析结果契约`
6. `feat(frontend): 展示分镜高光与资产`
7. `test(backend): 覆盖 CLI 沙箱与失败边界`
8. `refactor(worker)!: 移除旧 ASR 与模型 Provider`
9. `docs: 收口本机 CLI 视频分析运行说明`

每次提交前只暂存当前范围，运行对应最小充分门禁并通过提交信息校验。

## 14. 风险与控制

| 风险 | 控制 |
| --- | --- |
| 用户误解为完全本地推理 | UI/文档明确抽帧会发送云端模型，分析前提示 |
| 视频画面 Prompt Injection | 固定 Prompt + 断网 + 文件/工具/Secret 隔离 + 负向测试 |
| Codex `exec` 读取边界不足 | capability gate；不满足则改 app-server restricted read 或外层 OS sandbox |
| Claude Read/Bash 权限过宽 | project-root Read rules、绝对 sandbox workspace、精确 FFmpeg rules、dontAsk |
| CLI flag/输出随升级变化 | 支持版本/capability preflight、fake argv 测试、升级后真实 E2E |
| OAuth 被误当 SaaS 凭据 | 仅单机单用户；不远程暴露，不允许浏览器选择 Provider |
| 订阅额度/速率不足 | 并发 1、公共 timeout/资源限制、Claude max turns、稳定用量错误，不隐式 fallback |
| 快速闪切被漏判 | UI 披露取样不确定性，以受控 fixture 验证，不宣称逐帧 EDL |
| 模型输出合法但事实错误 | shot evidence、可信元数据校验、真实双 Provider 人工验收 |
| 子进程和磁盘泄漏 | 进程组 TERM/KILL、运行期 quota、attempt finally cleanup、恢复 sweeper |
| 容器运行规范冲突 | 最终切换同步更新 Compose、AGENTS、README 和 operations，不保留误导入口 |

## 15. 完成定义

只有同时满足以下条件，Plan 才能改为 Completed：

- `AC-010-01` 至 `AC-010-12` 全部通过并附证据。
- Codex 和 Claude 对同一受控视频各完成一次真实端到端分析。
- 全量后端、前端、OpenAPI、SQL、Compose/本机运行说明门禁通过。
- 旧 ASR、DeepSeek、Ollama、LangChain、transcript evidence 和旧 UI 已删除，无兼容双轨。
- 进程、目录、网络、工具、环境变量和日志安全测试全部 fail closed。
- 文档准确说明云端推理、本机 OAuth 单用户边界和视觉-only 限制。
- 工作区只剩任务开始前已经存在的用户改动，相关提交均可独立回滚。
