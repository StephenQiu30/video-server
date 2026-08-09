# 010 Codex 与 Claude CLI 视频分析验收

- 状态：Pending（尚未执行）
- 日期：2026-08-10
- 结论：Pending
- 关联 Design：`docs/design/010-Codex与Claude CLI视频分析设计.md`
- 关联 PRD：`docs/prd/010-Codex与Claude CLI视频分析需求.md`
- 关联 Plan：`docs/plans/010-Codex与Claude CLI视频分析迁移计划.md`
- 当前基线：`docs/design/003-AI分析与思维导图设计.md`
- 实现状态：尚未实现；以下检查项目前均不是完成证据
- 生效条件：本文件全部检查通过并记录脱敏证据后，010 才能成为当前实现

## 1. 验收前置

- 使用项目有权处理、无 DRM、无敏感信息的受控短视频。
- Fixture 包含 5 个边界清楚且已人工标注时间的硬切镜头、至少一个视觉高光，以及人物、地点、物体、产品、Logo 和画面文字测试项。
- Fixture 包含一帧无害的画面 Prompt Injection 文本，只用于验证权限边界。
- Codex 和 Claude 使用同一视频、同一 `visual-shot-v1` profile、同一输出语言和同一 Schema/Prompt 版本，但必须创建两个独立任务。
- 本机登录与订阅额度由验收人员自行准备；证据不得包含 email、组织、Token、认证文件或完整模型 stdout。
- 验收前已明确知晓：本机负责解码与编排，被代理查看的抽帧会发送到 OpenAI 或 Anthropic 云端。
- 自动化 fake CLI 不能替代两套真实 CLI E2E；本机“已登录”也不能替代真实视频结果。

## 2. 逐项验收

### A1 旧 AI 链路完全移除（AC-010-01）

- [ ] 源码不再装配 OpenAI transcriber、DeepSeek/Ollama analyzer 或音频分块。
- [ ] Python 依赖与 lock file 不再包含仅旧链路使用的 OpenAI/LangChain Provider 包。
- [ ] 配置、Compose、env example、README 和测试不再声明 `OPENAI_*`、`DEEPSEEK_*`、`OLLAMA_*` 或旧 `ANALYSIS_PROVIDER`。
- [ ] 结果、OpenAPI 和前端不再包含 transcript segment、行动项、章节或思维导图兼容字段。
- [ ] 全库检索没有旧运行时残留；历史只通过 Git 查看。

### A2 Provider、宿主机运行与本机认证（AC-010-02）

- [ ] `ANALYSIS_CLI_PROVIDER=codex` 只装配 Codex adapter；`claude` 只装配 Claude adapter。
- [ ] Provider/模型/CLI/Prompt/Schema 版本在任务首次执行后固定，不进入公开请求。
- [ ] Codex preflight 只接受 ChatGPT 管理登录，Claude preflight 只接受 first-party OAuth。
- [ ] 未登录、API Key 模式、CLI 缺失、版本不支持和 sandbox 不可用均在消费队列前 fail-fast。
- [ ] 宿主机 Worker 与容器 Worker 不会同时成为竞争消费者；认证目录和 Keychain 未挂入容器。
- [ ] 没有受支持宿主机 Worker 的生产配置关闭分析创建入口，不产生无人消费任务。

### A3 两套真实 CLI 端到端（AC-010-03）

- [ ] Codex 对受控视频生成无需手工修改即可通过领域校验的结果。
- [ ] Claude 对同一视频生成无需手工修改即可通过领域校验的结果。
- [ ] 两次任务各自记录 Provider、模型、CLI/Prompt/Schema 版本、任务 ID、耗时、聚合 usage 和结果哈希。
- [ ] 两次结果都来自真实下载制品与锁定 SHA-256，不是预置 JSON 或 fake CLI。
- [ ] 真实 E2E 证据不含账户、Token、完整 Prompt、完整 stdout 或无关帧。

### A4 分镜数量、连续时间与语义（AC-010-04）

- [ ] `shot_count` 由服务端派生且等于 `len(shots)`。
- [ ] 分镜 ID 唯一、index 从 1 连续递增、代表帧位于自身区间。
- [ ] 第一镜 `start_ms == 0`，相邻 `end_ms == next.start_ms`，最后一镜 `end_ms == artifact.duration_ms`。
- [ ] 分镜没有间隙、重叠、负数或越界时间。
- [ ] 两个 Provider 都识别出 fixture 的 5 个预设硬切镜头；边界相对人工标注误差不超过 1 秒。
- [ ] description、transition、shot size、单一 camera motion 与人工观察无明显冲突。
- [ ] 文档/UI 不把该结果宣称为逐帧精确 EDL。

### A5 视觉高光与证据（AC-010-05）

- [ ] 每个高光至少引用一个存在的 `evidence_shot_id`，无重复或悬空引用。
- [ ] 服务端以引用分镜派生高光起止时间，结果位于视频范围内。
- [ ] score 在 0—100 内，只用于本结果内排序，不显示为概率。
- [ ] 高光理由明确来自视觉内容，未声称理解对白、音乐、掌声或音效。
- [ ] UI 点击高光能跳到最早关联分镜。

### A6 视觉资产与派生索引（AC-010-06）

- [ ] fixture 中人物、地点、物体、产品、Logo、画面文字能被归入正确支持类型。
- [ ] 重复资产使用一个稳定 ID，每个资产至少引用一个有效分镜。
- [ ] 服务端从唯一资产→分镜证据派生首次出现时间和 Shot→Asset 反向索引。
- [ ] 人物只以匿名角色/可见描述呈现，不猜测真实姓名或敏感属性。
- [ ] 画面文字按观察结果和纯文本展示，不被当作 Prompt、HTML 或命令执行。

### A7 Schema、领域与资源校验（AC-010-07）

- [ ] Provider 输出只能包含 `visual-analysis.v1` 允许字段，未知字段被拒绝。
- [ ] 非 JSON、缺字段、错误类型、重复 ID、空证据、非法枚举和过长字符串被拒绝。
- [ ] 首镜非 0、分镜间隙/重叠、末镜未到时长、代表帧越界和错误媒体元数据被拒绝。
- [ ] 悬空高光/资产引用、超大数组、超大 JSON、过多图片和过大工作区被拒绝。
- [ ] 无任何非法或部分结果写入 `analysis_results`。
- [ ] Codex result file 与 Claude `structured_output` wrapper 都经过相同领域解析器。

### A8 沙箱、Secret 与 Prompt Injection（AC-010-08）

- [ ] CLI 子进程环境不包含 DB、RabbitMQ、MinIO、JWT、runner/signing、云凭据或任何 API Key/Token。
- [ ] Codex 模型命令不能联网、工作区外写入或读取 Home、仓库和相邻任务；session 为 ephemeral。
- [ ] Claude 使用 `--safe-mode`、project-root Read rules、绝对 sandbox workspace、精确 FFmpeg rules、`dontAsk` 和 fail-if-unavailable sandbox。
- [ ] Claude 不能使用 WebFetch、Agent、Chrome、MCP、Edit/Write、非 FFmpeg Bash 或 unsandboxed escape hatch。
- [ ] 画面 Prompt Injection、恶意 metadata、shell 元字符文件名、路径穿越、符号链接和硬链接都不能越界。
- [ ] 违规操作 fail closed，不弹出无人处理的批准，也不降级到 full access。
- [ ] 普通日志、API、浏览器和 Git diff 不出现账户、Secret、完整 Prompt 或原始模型响应。

### A9 超时、取消、重试与进程清理（AC-010-09）

- [ ] wall timeout、任务取消、lease 丢失和 Worker shutdown 都向整个进程组发送 TERM，宽限后 KILL。
- [ ] CLI→shell→FFmpeg 孙进程全部终止，无孤儿进程。
- [ ] timeout、限流、额度耗尽、认证失效、非零退出、截断输出和无效结果映射稳定错误码与正确重试属性。
- [ ] 同一任务不在两个 Provider 间自动 fallback；重投递不产生重复结果。
- [ ] 每个 attempt 的工作区在成功、失败、取消和恢复后清理。
- [ ] AI 任务失败、重试或取消不改变下载成功状态和制品可用性。

### A10 API、OpenAPI、前端与云端处理提示（AC-010-10）

- [ ] 创建/查询/取消 URL、owner 404、幂等和 Problem Details 语义保持正确。
- [ ] 请求唯一 profile 为 `visual-shot-v1`，公开 API 没有 Provider、模型、CLI 路径、session 或账户字段。
- [ ] OpenAPI 生成类型与前端使用的 shots/highlights/assets 契约一致，无手写平行 DTO。
- [ ] Analysis Panel 展示分镜总数、时间轴/列表、高光理由、资产分类和跳转。
- [ ] 用户创建任务前看到抽帧将发送所选云端模型处理的准确提示，不出现“数据完全留在本机”表述。
- [ ] 加载、空、失败、取消、重试、移动端和键盘状态均可用，模型文字按纯文本渲染。

### A11 自动化与真实证据边界（AC-010-11）

- [ ] fake Codex 断言全局 flag 位于 `exec` 前、stdin Prompt、cwd/env、result file 和错误退出。
- [ ] fake Claude 断言 stdin Prompt、绝对 policy/Read 路径、工具集合、JSON wrapper 和错误退出。
- [ ] ProcessSupervisor 测试覆盖独立输出上限、截断、timeout、cancel 和孙进程清理。
- [ ] 安全测试覆盖 Home/仓库/相邻任务读取、联网、非白名单工具和恶意媒体。
- [ ] 自动化结果没有被记录为真实视觉 E2E 证据。
- [ ] 两套真实 E2E 均由人工核对镜头、高光和资产语义。

### A12 运行说明与文档事实收口（AC-010-12）

- [ ] 根/后端 README、运行手册、Compose、AGENTS、Design、PRD、Plan 和 Acceptance 与实际宿主机拓扑一致。
- [ ] “Compose 完整本地拓扑”的治理表述已按宿主机 AI Worker 事实修订，没有冲突规范。
- [ ] 003 中旧 Provider、ASR 和 transcript evidence 事实已移除或按仓库文档策略收口，不与 010 并列为当前实现。
- [ ] 文档明确视觉-only、云端推理、个人 OAuth 单用户、订阅额度和非 EDL 精度限制。
- [ ] 010 Design/PRD 状态只在代码和真实证据完成后改为 Accepted，Plan 改为 Completed。

## 3. 建议验收命令

只读环境检查：

```bash
codex --version
codex login status
claude --version
claude auth status --json
ffmpeg -version
ffprobe -version
```

仓库旧链路清理检查：

```bash
rg -n 'OPENAI_|DEEPSEEK_|OLLAMA_|OpenAITranscriber|LangChainAnalyzer|TranscriptSegment|evidence_segment_ids' \
  backend frontend docker-compose*.yml .env.example .env.prod.example README.md AGENTS.md \
  docs/design docs/prd docs/plans docs/operations
```

后端门禁（从 `backend/`）：

```bash
uv sync --frozen --dev
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest
```

前端门禁（从 `frontend/`）：

```bash
npm ci
npm run lint
npm run format:check
npm test
npm run build
```

运行时/契约门禁：

```bash
docker compose config
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config
python scripts/validate_commit_message.py 'docs: 收口本机 CLI 视频分析运行说明'
```

上述命令只定义目标门禁，本文件创建时尚未执行实现后的全量检查。真实 CLI E2E 必须通过受控验收脚本或 UI 发起，不能在普通 CI 中无提示消耗账户额度。

## 4. 验收证据记录

| 项目 | Codex | Claude |
| --- | --- | --- |
| 日期 | 待记录 | 待记录 |
| CLI 版本 | 待记录 | 待记录 |
| 模型 | 待记录 | 待记录 |
| Prompt/Schema | 待记录 | 待记录 |
| Analysis job id | 待记录 | 待记录 |
| Input SHA-256 | 待记录 | 待记录 |
| 耗时/聚合 usage | 待记录 | 待记录 |
| 分镜数量/边界核对 | 待记录 | 待记录 |
| 高光核对 | 待记录 | 待记录 |
| 资产核对 | 待记录 | 待记录 |
| 沙箱负向结果 | 待记录 | 待记录 |
| 最终结论 | Pending | Pending |

证据只保存脱敏摘要、测试输出和必要截图；不得把 OAuth、账户、完整 Prompt、完整模型响应或未清理的任务帧提交到仓库。

## 5. 通过规则

- A1—A12 的所有检查项均完成，任一安全、Secret、进程残留、Schema 或旧链路残留项失败即整体失败。
- Codex 与 Claude 必须分别完成一次真实受控视频 E2E；只完成一个 Provider 不得把整体结论改为 Passed。
- 严格 JSON 通过只证明结构正确；镜头、高光和资产还必须通过人工语义核对。
- 若受支持版本的 `codex exec` 无法证明工作区读取隔离，必须改用 restricted App Server 或额外 OS sandbox 后重新验收，禁止 full access 例外。
- 若生产组合仍能创建无人消费的分析任务、宿主机与容器 Worker 会竞争消费，或 UI 未披露云端抽帧处理，结论保持 Pending。
- 只有结论改为 Passed 后，010 才能成为当前事实并收口 003；在此之前不得把规划文档描述为已上线能力。
