# 010 Codex 与 Claude CLI 视频分析需求

- 状态：Implemented（Claude Provider 当前环境未通过视觉验收）
- 日期：2026-08-10
- 关联 Design：`docs/design/010-Codex与Claude CLI视频分析设计.md`
- 当前实现：`visual-analysis.v1`、宿主机 Analysis Worker、Codex 默认 Provider
- 验收状态：Codex 真实 E2E 通过；Claude 当前本机模型路由不具备可用视觉理解

## 1. 背景与用户问题

当前 AI 功能先转录音频，再从文字生成摘要、章节和思维导图。用户真正需要的是理解视频画面本身：视频有多少分镜、每个分镜展示什么、哪些画面是高光、有哪些可以复用或检索的视觉资产。

本机已经安装并登录 Codex CLI 和 Claude Code CLI。继续维护 OpenAI ASR Key、DeepSeek Key 或 Ollama 模型既没有解决视觉证据问题，也让启动和部署变复杂。产品需要改为宿主机本地 CLI 编排、云端模型推理、受限本地画面解码的单用户分析模式。

## 2. 用户与核心任务

首期目标用户是已经在同一台可信电脑上登录 Codex/Claude、并运行本项目的单个本地用户。

核心任务：

1. 用户完成一个合法视频下载。
2. 用户在下载详情中启动“视觉分镜分析”。
3. 系统使用管理员预先配置的 Codex 或 Claude CLI 分析锁定的视频制品。
4. 用户看到分析阶段和稳定错误状态。
5. 成功后，用户查看分镜总数、分镜时间与内容、视觉高光和资产目录，并能跳转到对应时间。

## 3. 产品目标

- 用 AI 视觉能力替换 transcript-first 分析，使结论直接引用分镜。
- 项目不保存或分发 OpenAI、Anthropic、DeepSeek、Ollama API Key。
- 两个 CLI Provider 使用同一业务结果，不在前端形成两套产品体验。
- AI 分析失败、额度耗尽或未登录时，下载制品仍可正常使用。
- 对进程、目录、网络、输出和资源建立可自动验证的安全边界。
- 在用户启动分析前准确披露：本机负责解码/编排，被代理查看的抽帧会发送到所选云端模型。

## 4. 非目标

- 音频转录、对白摘要、说话人识别、音乐或音效高光。
- 应用侧本地镜头检测算法或固定阈值 scene detection。
- 逐帧法证分析、专业剪辑 EDL、帧级无误差保证。
- 人物真实身份识别或敏感属性推断。
- 用户自定义 Prompt、模型、CLI 参数、工具、文件路径或 Provider。
- 多租户共享个人 Codex/Claude 登录、远程托管 CLI 或容器内复制 OAuth。
- 同一任务在两个 Provider 之间自动 fallback、投票或并行对比。

## 5. 功能需求

### FR-010-01 本机 CLI Provider

- 系统必须支持 `codex` 与 `claude` 两个 Provider，并通过可信 Worker 配置二选一。
- Provider 选择不得进入公开 API 请求、前端设置或用户可编辑任务数据。
- 每个任务首次执行后必须固定 Provider、模型、CLI、Prompt 和 Schema 版本。
- 任一 Provider 失败时不得静默调用另一个 Provider。

### FR-010-02 复用本机登录环境

- Codex 必须复用 `codex login` 的 ChatGPT 管理登录；Claude 必须复用 Claude Code 的 first-party OAuth 登录。
- 项目 `.env`、数据库、前端、API、日志和测试 fixture 不得包含 AI Token 或 API Key。
- Worker 启动前必须检查 CLI 是否存在、版本是否受支持、所需 flag 是否可用以及认证是否有效。
- 未登录、认证方式不允许或沙箱不可用时，Worker 必须 fail-fast，不能开始消费任务。

### FR-010-03 AI 自主视频分析

- AI 代理必须在单任务隔离目录中自主使用受限 `ffprobe`、`ffmpeg` 和图片查看能力观察视频。
- AI 必须先建立整段粗粒度覆盖，再对可疑边界或高光区间加密取样。
- 应用只能提供视频、可信元数据、工具、Prompt、Schema 和资源上限，不能在业务代码中计算分镜结果。
- 视频帧、容器元数据、字幕和画面文字必须被视为不可信输入，不能改变工具权限或输出契约。
- 产品必须在创建任务前提示抽帧会由 OpenAI 或 Anthropic 云端模型处理；不得宣称数据完全留在本机。

### FR-010-04 分镜结果

- 成功结果必须返回 `shot_count` 和完整 `shots` 列表。
- 每个分镜必须包含稳定 ID、顺序、起止时间、代表帧时间、画面描述、入场转场、景别、单一镜头运动枚举和视觉标签。
- 分镜采用左闭右开区间并严格连续覆盖 `[0, duration_ms)`：第一镜从 0 开始、相邻边界相等、最后一镜结束于权威视频时长。
- `shot_count` 必须由服务端从分镜数组长度派生，不能要求模型重复统计。
- UI 必须能从分镜跳转到视频对应开始时间。

### FR-010-05 视觉高光

- 结果必须返回零个或多个视觉高光。
- 每个高光必须包含标题、描述、0—100 相对分值、视觉理由和至少一个有效 `evidence_shot_id`；起止时间由服务端从引用分镜派生。
- 高光只能基于可见画面，不得声称依据对白、音乐、掌声或音效。
- UI 必须展示高光理由，并能跳转到最早关联分镜。

### FR-010-06 视觉资产目录

- 结果必须对重复出现的视觉资产去重，支持 `person`、`location`、`object`、`product`、`logo` 和 `on_screen_text`。
- 每个资产必须包含稳定 ID、类型、标签、描述和至少一个有效 `evidence_shot_id`。
- 首次出现时间和分镜到资产的反向索引必须由服务端从唯一的资产→分镜证据方向派生。
- 人物资产只描述可见特征或匿名角色，不猜测真实身份和敏感属性。

### FR-010-07 严格 JSON 与分镜证据

- 两个 Provider 必须使用同一 `visual-analysis.v1` JSON Schema。
- Provider 的 structured output 成功不替代应用校验；应用必须再次校验字段集合、类型、大小、连续时间分区、引用和媒体元数据，并补齐确定性派生字段。
- 任何未知字段、非法时间、悬空引用、重复 ID、越限数组或超大结果都必须拒绝，不能保存部分成功结果。
- 公开结果不得包含 CLI stdout wrapper、session id、账户、原始 Prompt、工具日志或 Provider 私有字段。

### FR-010-08 任务、取消、重试与稳定错误

- 继续复用分析任务的幂等、lease/heartbeat、retry wait、取消和 artifact retention lock。
- 阶段必须收敛为 `preparing`、`analyzing`、`validating`，不再显示 `transcribing`。
- 取消、超时、lease 丢失和 Worker shutdown 必须终止 CLI 及其全部 FFmpeg 子进程。
- CLI 缺失、版本不支持、未登录、沙箱不可用、额度耗尽、限流、超时、资源越限和非法输出必须映射稳定错误码。
- AI 失败不得更改下载任务或下载制品状态。

### FR-010-09 权限隔离与不可信媒体

- 每个 attempt 必须有独立 `0700` 工作区，输入使用固定安全文件名，成功或失败后清理。
- CLI 子进程不得继承数据库、RabbitMQ、MinIO、签名、云凭据或 API Key 环境变量。
- 模型生成的命令不得联网、读取 Home/仓库/其他任务或在工作区外写文件。
- Claude 必须限制为受控 Bash/Read 工具并强制 OS sandbox；Codex 必须使用 workspace sandbox、断网、无批准等待和 ephemeral session。
- 不得使用 full access、跳过沙箱、Chrome、WebFetch、web search、MCP、插件、subagent 或 unsandboxed escape hatch。
- 工作区字节、文件、图片、wall-clock、stdout/stderr 和结果大小必须有硬上限；Claude 另外限制 turn。

### FR-010-10 API 与前端结果呈现

- 分析资源的创建、查询和取消 URL 保持不变；请求 profile 唯一值改为 `visual-shot-v1`。
- OpenAPI 是新结果的唯一前后端契约，前端类型必须重新生成。
- Analysis Panel 必须显示分镜总数、分镜时间轴/列表、高光和资产目录，并为加载、空、失败、取消和重试提供明确状态。
- 旧转录阶段、行动项、章节和思维导图 UI 必须删除，不保留兼容切换。
- 所有模型文字按纯文本渲染，不能作为 HTML、Markdown 指令或命令执行。

### FR-010-11 宿主机运行与运维

- `worker-analysis` 必须直接以本机用户身份运行，不能从 Docker 容器读取宿主机 OAuth。
- README、运行手册、Compose 和项目协作规范必须准确说明宿主机 AI Worker 的启动边界。
- 没有受支持宿主机 Worker 的生产组合必须关闭分析创建入口，不能积压无人消费的任务。
- 系统不得自动弹出登录浏览器；认证失效时应给出本机命令提示，由用户在终端主动登录后重启 Worker。
- 首期并发必须为 1；配置变更只影响新任务，不能改变正在运行的任务。

## 6. 非功能需求

### NFR-010-01 安全

- 所有媒体和模型输出默认不可信，权限控制依赖 OS sandbox 与工具限制，而不是只依赖 Prompt。
- Secret 不进入 CLI 子进程、普通日志、结果、API、前端或版本库。
- 越界读写、联网、非白名单工具和沙箱降级必须 fail closed。

### NFR-010-02 可靠性

- 进程必须在超时、取消和异常时收敛，不留下 CLI/FFmpeg 孤儿进程或未清理工作区。
- 同一任务重投递不得产生重复结果，任务结果与固定 input SHA-256 一致。
- 任何非法模型输出都不得写入 `analysis_results`。

### NFR-010-03 可观测性与隐私

- 只记录 Provider、模型、CLI/Prompt/Schema 版本、耗时、退出分类、聚合 usage、帧数和结果大小。
- 不记录账户、完整 Prompt、完整帧列表、原始 stdout、原始模型响应或 OAuth 文件路径。
- 错误信息必须对用户可行动，但不能泄漏本机目录和 Secret。

### NFR-010-04 性能与容量

- 时长、图片数、图片尺寸、工作区、输出、超时和并发均由类型化配置限制；Provider 特有上限只能放在对应 Provider 配置中。
- 父进程必须在运行期间监控资源，而不是只在任务结束后检查。
- 超出首期容量的输入必须稳定拒绝，不允许无界降质或无界消耗订阅额度。

### NFR-010-05 可维护性

- 领域和应用层不得导入 Codex/Claude SDK 或 CLI 私有模型。
- 两个适配器只在基础设施层存在，共享端口、结果 Schema、错误分类和进程监管。
- 完成切换后删除旧 Provider、旧 ASR、旧结果和旧配置，不维护双轨兼容。

## 7. 验收标准

- `AC-010-01`：仓库中不再存在运行时 OpenAI ASR、DeepSeek、Ollama、LangChain 配置、依赖或实现；`.env` 不需要 AI Key。
- `AC-010-02`：可信配置可分别启动 Codex 和 Claude Worker；两者都复用允许的本机登录，未登录时 fail-fast。
- `AC-010-03`：同一个受控短视频通过 Codex 和 Claude 各生成一个通过 `visual-analysis.v1` 校验的结果。
- `AC-010-04`：受控视频的服务端派生 `shot_count` 与分镜数组一致，分镜从 0 到权威时长形成无间隙、无重叠的连续分区，人工核对能覆盖预设硬切镜头。
- `AC-010-05`：每个高光只引用有效分镜，理由明确为视觉依据，跳转时间有效。
- `AC-010-06`：人物、地点、物体、产品、Logo、画面文字 fixture 能形成去重资产，资产只引用有效分镜，首次出现时间和反向索引由服务端正确派生。
- `AC-010-07`：未知字段、非法 JSON、悬空引用、重复 ID、越界时间、错误媒体元数据、超大数组和超大结果全部被拒绝。
- `AC-010-08`：画面 Prompt Injection、恶意元数据和符号链接不能获得网络、Home、仓库、其他任务或 Secret。
- `AC-010-09`：超时、取消、lease 丢失和 Worker shutdown 都会终止完整进程组并清理工作区。
- `AC-010-10`：API/OpenAPI/前端只呈现 Provider 无关的新结果，创建前明确披露抽帧云端处理，AI 失败不影响下载制品。
- `AC-010-11`：fake CLI 自动化覆盖两套 argv、输出 wrapper、错误映射和安全边界；真实账户调用不进入普通 CI。
- `AC-010-12`：README、运行手册、Compose、003/010 文档与代码当前态一致，不保留旧 Provider 兼容说明。

## 8. 发布成功信号

- 两套真实 CLI 对同一受控视频均完成端到端分析，且没有手工修改模型 JSON。
- 受控硬切视频的分镜数量和时间范围达到验收 fixture 的人工标注要求。
- 所有高光和资产都能回溯到分镜，不出现 transcript evidence 或悬空 ID。
- 取消后没有 CLI/FFmpeg 孤儿进程，任务目录在宽限期内清理。
- API、浏览器、普通日志和 Git diff 均不出现 AI Token、账户或原始模型响应。

## 9. 首期不包含

音频理解、字幕抽取、人物身份识别、逐帧精确镜头检测、跨视频资产库、向量检索、视频问答、用户 Prompt、多 Provider 对比、远程 CLI 主机、多租户 SaaS 和自动内容发布。

## 10. 依赖与已知限制

- 依赖受支持版本的 Codex CLI、Claude Code CLI、FFmpeg 和 FFprobe，以及用户已经完成的本机订阅登录。
- CLI 自身需要访问各自模型服务；AI 生成的本地命令仍必须断网。
- 被代理查看的抽帧会发送给 OpenAI 或 Anthropic；“本机 CLI”不是本地模型，也不是数据不出机承诺。
- 不使用项目 API Key 不代表没有订阅额度、速率、月度信用或自动化使用限制。
- Claude/Codex 对图片的尺寸、数量和上下文有上限；极短闪切和复杂转场可能被漏判。
- 本机 OAuth 只适用于可信单用户本地模式；若未来提供多用户服务，必须重新设计商业认证和隔离，不能沿用本需求。
