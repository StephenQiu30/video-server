# 010 Codex 与 Claude CLI 视频分析验收

- 状态：Partially Passed
- 日期：2026-08-10
- 结论：Not Passed（Codex 通过；Claude 当前本机模型路由未通过视觉 E2E）
- 关联 Design：`docs/design/010-Codex与Claude CLI视频分析设计.md`
- 关联 PRD：`docs/prd/010-Codex与Claude CLI视频分析需求.md`
- 关联 Plan：`docs/plans/010-Codex与Claude CLI视频分析迁移计划.md`
- 当前运行时：默认 `ANALYSIS_CLI_PROVIDER=codex`

## 1. 验收范围

本次已执行代码迁移、自动化门禁、Codex/Claude CLI preflight、Codex 真实视觉 E2E，以及 Claude 多模型档位的真实图片/视频诊断。受控输入是项目本机生成的 8 秒、640×360、24 fps、4 段硬切无音频视频；四段分别为红/蓝/绿/黄背景和位置/颜色不同的方块，不含敏感数据。

真实推理均复用本机 OAuth，不设置或读取项目 AI API Key。被代理查看的帧会发送给对应云端模型；本验收不宣称数据完全留在本机。

## 2. 实现验收结果

| 项目 | 结果 | 证据摘要 |
| --- | --- | --- |
| 旧 AI 链路移除 | Passed | OpenAI ASR、DeepSeek/Ollama/LangChain 适配器、音频分块、旧结果和旧 UI 已删除；运行配置无 AI Key |
| 公共视觉契约 | Passed | `visual-analysis.v1`；服务端派生 media、shot count、高光时间、资产首次出现时间和反向索引 |
| 分镜领域校验 | Passed | 严格拒绝未知字段、非法类型、重复 ID、空/悬空证据、间隙、重叠、越界和非法枚举 |
| 进程监管 | Passed | stdin Prompt、独立 stdout/stderr 上限、wall timeout、取消和进程组 TERM→KILL 有自动化覆盖 |
| 工作区策略 | Passed | 固定只读输入、regular file/realpath、符号链接/硬链接、文件/字节/图片配额；CLI 临时 FIFO/socket 只允许在 `tmp/` |
| Codex 权限 | Passed | 0.147.0 permission profile：任务根只读，`work/output/tmp` 可写，Home 不可读，模型命令断网，FFmpeg 可执行 |
| Claude 权限 | Passed | 2.1.226 safe mode、绝对任务 Read 规则、精确 FFmpeg Bash、无 MCP/网络；事件流 `permission_denials=[]` |
| API/OpenAPI/UI | Passed | 公开契约只含分镜、高光、资产；前端展示视觉摘要和三个结果页签，并披露抽帧云端处理 |
| 宿主机拓扑 | Passed | Compose 不再启动 Analysis Worker；开发环境由宿主机 Worker 复用本机 OAuth，生产默认关闭分析入口 |
| 宿主机 Worker 启停 | Passed | 本机配置下通过 preflight 并保持运行；接收 SIGINT 后正常退出，exit code 0 |
| 数据库当前态 | Passed | ORM 与 `backend/sql/schema.sql` 已同步；依仓库规范不保留 migration 目录，新数据卷按当前 schema 初始化 |
| Codex 真实视频 E2E | Passed | 适配器、结构化输出、领域解析全链路通过，无手工修改 JSON |
| Claude 真实视频 E2E | Failed | 三个模型别名实际路由到 `deepseek-v4-pro`，Read 返回 PNG 后模型仍误判为空，最终耗尽 turns |

## 3. Codex 真实 E2E 证据

| 字段 | 结果 |
| --- | --- |
| CLI / 登录 | `codex-cli 0.147.0` / ChatGPT managed login |
| 配置模型 | `gpt-5.6-sol` |
| Prompt / Schema | `visual-shot.v1` / `visual-analysis.v1` |
| 输入 SHA-256 | `e8616d404287bc1b790fe0cd0e04fde0132e91a38001dd573e25fa70a16632e2` |
| 原始结构化结果 SHA-256 | `491030ec23b4a3f045b9881fd102e2e1439504e97a74d07b055f02b7a5558c0f` |
| 分镜 | 4 个：`[0,2000)`、`[2000,4000)`、`[4000,6000)`、`[6000,8000)` ms |
| 高光 / 资产 | 2 / 1 |
| AI 取证文件 | 2 个接触表/边界图片 |
| 服务端校验 | Passed；连续分区、代表帧、引用、派生字段全部有效 |

人工核对：4 个硬切边界与 fixture 完全一致；描述正确识别四色背景、白/黑方块、静态镜头和高对比收尾。该证据来自隔离适配器 E2E，不是 RabbitMQ/API 创建的持久化任务，因此没有 Analysis job id；完整队列级真实任务仍需后续运行环境验收。

## 4. Claude 失败证据与根因

| 字段 | 结果 |
| --- | --- |
| CLI / 登录 | Claude Code `2.1.226` / first-party OAuth |
| 测试模型别名 | `sonnet`、`haiku`、`opus` |
| 实际 modelUsage | `deepseek-v4-pro` 或 `deepseek-v4-pro[1M]` |
| 文件/权限 | Read 工具成功返回 PNG base64；`permission_denials=[]` |
| 模型行为 | 把已返回的图片误判为“空”，反复 Read/抽帧 |
| 终止原因 | `subtype=error_max_turns`、`terminal_reason=max_turns` |
| 应用错误码 | `analysis_resource_limit` |

这证明 Claude adapter、OAuth、sandbox、Bash/Read 和图片传输链路能够启动，但本机当前实际模型路由不具备可用的视觉理解。不能仅凭 `claude auth status` 或图片工具返回成功把 Claude 标记为已验收。默认 Provider 必须保持 Codex；启用 Claude 前需要换到真实支持视觉的模型路由并重跑同一 E2E。

## 5. 自动化与构建门禁

- 后端：当前完整工作区 `400 passed`、mypy 222 个源码模块通过；只包含本次 AI 提交的隔离工作树 `371 passed`、mypy 214 个源码模块通过。两者的全量 Ruff lint/format 与冻结依赖安装均通过。
- 前端：25 个测试文件、81 个测试全部通过；Next.js 生产构建通过。
- 前端 lint/typecheck/format 通过；Biome 仅报告仓库既有 `.agents/skills` 断链符号链接警告。
- Compose 本地和生产组合均通过 `config --quiet`。

## 6. 尚未通过的验收项

- Claude 必须在真实支持视觉的模型路由上生成一个无需手工修改、通过领域 validator 的结果。
- 需要通过 API/RabbitMQ/MinIO/数据库执行一次完整持久化任务，而不只是隔离适配器 E2E。
- 需要补充包含人物、产品、Logo、画面文字和画面 Prompt Injection 的人工 fixture；本次简单 fixture 只验证硬切、视觉高光和物体资产。
- 需要在真实任务中验证取消/lease 丢失后的 CLI→shell→FFmpeg 孤儿进程清理；当前证据来自自动化进程树测试。

## 7. 最终判定

010 已成为代码和文档的当前实现，Codex 路径可以作为本机单用户默认能力；整体双 Provider Acceptance 仍为 `Not Passed`。按运维决策，生产 API 默认开启 `ANALYSIS_ENABLED=true`，生产 Compose 仅向 loopback 发布宿主机 Worker 必需的 PostgreSQL、RabbitMQ 和 MinIO 端口；这不代表 Claude 或完整生产验收通过。Claude 视觉 E2E、完整队列级 E2E和剩余安全 fixture 完成后，才可把本文件改为 Passed。
