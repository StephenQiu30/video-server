# AI 分析 Agent 与 Provider 运行手册

## 1. 首次使用

在 `backend` 目录执行。Windows、macOS 和 Linux 共用以下 Agent 管理命令；只有宿主机的服务注册方式由平台适配层处理，分析任务、队列和恢复语义保持一致：

```powershell
uv run python -m app.workers.analysis.agent_cli doctor
uv run python -m app.workers.analysis.agent_cli install
uv run python -m app.workers.analysis.agent_cli status
```

macOS/Linux 使用相同的 `uv run python ...` 命令。`doctor` 必须先成功；它会按活动 Provider 检查 Codex/Claude CLI 或 DeepSeek 适配器、FFmpeg、FFprobe，以及 `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` 对固定就绪探针的读取权限。

命令默认读取仓库根目录 `.env`。若业务服务使用 `.env.prod`，必须让宿主机 Agent
读取同一文件，不能把开发 Agent 接到生产 API：

```powershell
uv run python -m app.workers.analysis.agent_cli doctor --env-file ../.env.prod
uv run python -m app.workers.analysis.agent_cli install --env-file ../.env.prod
```

`install` 会把环境文件的绝对路径写入系统服务参数，重启和登录后仍保持同一环境。

`install` 是幂等更新命令：它会先确认当前项目 Agent 已停止，再写入并启动最新服务定义，最后验证服务确实处于运行状态。三个平台共用同一把当前用户进程锁；即使误执行第二个 `agent_cli run` 或直接启动 Worker，后启动的进程也会立即退出，不会形成两个队列消费者。服务管理器停止、启动或状态确认失败时命令直接失败，不会继续覆盖定义或伪报成功。

从旧版本首次升级时，`install` 和 `uninstall` 会一次性处理已删除的旧启动入口：macOS 只停止标签、Python、工作目录和模块都与本项目严格匹配的旧 LaunchAgent；Linux 只停止 PID 文件、进程参数和工作目录都严格匹配的旧 Worker。任一身份校验失败都会拒绝发送信号并要求人工核对，不会按模糊进程名结束其他程序。

默认 Profile 是“本机 Codex”。先在同一系统用户下执行 `codex login`，再运行 doctor。Claude 本机模式同理使用 `claude` 自己的登录命令。

## 2. 配置 API 服务

管理员登录后打开 `/admin/ai-providers`：

1. 新增 Provider。
2. 选择 Codex CLI、Claude CLI 或 DeepSeek API。DeepSeek 会固定使用官方视觉模型并自动填写官方 Base URL。
3. API Key 线路填写 HTTPS Base URL 与 Key；Codex/Claude 可填写模型，DeepSeek 的模型字段按适配器契约锁定。
4. 保存后点击“启用”。
5. 下一条新分析任务自动使用新线路。

第三方 Key 不放入 `.env`，也不要求 C 端用户配置。未新增或未启用第三方 Profile 时，当前态 schema 提供的 `local-codex` 始终是默认线路。

`local-codex` 是服务端保留的可恢复兜底：无论当前是否启用都不能删除，也不能改变 Codex 引擎、宿主机登录认证、空 Endpoint 和无凭据结构。管理页仅允许调整显示名称与模型。

Key 保存后不会回显。编辑时留空表示保留旧 Key；如需删除密钥，删除对应的非活动 Profile。

## 3. 平台服务位置

| 平台 | 服务定义 | 日志 |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\FrameFetch\analysis-agent.xml` / 任务 `FrameFetchAnalysisAgent` | 事件与任务计划程序历史 |
| macOS | `~/Library/LaunchAgents/com.framefetch.analysis-agent.plist` | `~/Library/Logs/FrameFetch/` |
| Linux | `~/.config/systemd/user/framefetch-analysis-agent.service` | `~/.local/state/framefetch/` 与 `journalctl --user` |

Linux 如果要求注销后仍运行，需要由运维显式执行 `loginctl enable-linger <user>`；本项目安装命令不自动扩大该权限。

## 4. 常见故障

### Agent 状态未确认

```text
uv run python -m app.workers.analysis.agent_cli status
uv run python -m app.workers.analysis.agent_cli doctor
```

依次确认：活动 Profile 存在、CLI 可执行、登录有效、FFmpeg/FFprobe 可执行、PostgreSQL/RabbitMQ/MinIO 地址对宿主机可达。Agent 状态未确认不会阻止 API 接收任务；任务会保持 `queued`，直到 Agent 恢复并消费消息。

若本机使用仓库基础环境且 `doctor` 返回 MinIO readiness probe 缺失，在 `backend` 目录执行 `docker compose --env-file ../.env -f ../docker-compose-env.yml run --rm minio-init`，由环境初始化任务幂等创建 `video-artifacts` bucket 与 `system/analysis-readiness` 探针。外部或生产 MinIO 应由其管理员创建同名探针，不能另起一套本机 MinIO 掩盖连接错误。若返回凭据无法读取，再确认统一 AK/SK 的 bucket 读取权限，并检查 `.env` 或 `.env.prod` 中唯一的 `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`。

### 本机登录不可用

系统服务必须与执行登录命令的用户一致。不要把用户登录文件复制到 Docker。重新登录后重启 Agent 服务，或重新执行 `install` 更新服务定义。

### API Key Provider 失败

确认协议与引擎匹配：Codex 只支持 Responses；Claude 要求 Anthropic Messages；DeepSeek 使用 `deepseek-v4-flash-vision-exp` 和官方 OpenAI 兼容接口。Base URL 通常是服务根或 `/v1` 根，不要填写完整的单次请求路径。Key 不会显示在日志中；必要时在管理页覆盖写入新 Key。

### 卸载

```text
uv run python -m app.workers.analysis.agent_cli uninstall
```

卸载会先验证当前项目的新旧 Agent 进程均已停止，再移除当前项目创建的用户服务定义。停止或后置状态验证失败时会保留定义并返回失败，不会留下无法管理的后台进程。卸载不删除数据库 Profile、CLI 登录态、视频制品或报告；进程锁文件是无凭据的固定状态文件，可保留供后续重装复用。
