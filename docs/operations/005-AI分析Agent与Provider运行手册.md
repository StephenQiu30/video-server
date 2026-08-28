# AI 分析 Agent 与 Provider 运行手册

## 1. 首次使用

在 `backend` 目录执行。Windows、macOS 和 Linux 共用以下 Agent 管理命令；只有宿主机的服务注册方式由平台适配层处理，分析任务、队列和恢复语义保持一致：

```powershell
uv run python -m app.workers.analysis.agent_cli doctor
uv run python -m app.workers.analysis.agent_cli install
uv run python -m app.workers.analysis.agent_cli status
```

macOS/Linux 使用相同的 `uv run python ...` 命令。`doctor` 必须先成功；它会检查数据库中的活动 Provider、Codex/Claude CLI、FFmpeg、FFprobe、本机登录状态，以及 `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` 对固定就绪探针的读取权限。

默认 Profile 是“本机 Codex”。先在同一系统用户下执行 `codex login`，再运行 doctor。Claude 本机模式同理使用 `claude` 自己的登录命令。

## 2. 配置 API 服务

管理员登录后打开 `/admin/ai-providers`：

1. 新增 Provider。
2. 选择 Codex CLI（服务必须兼容 Responses）或 Claude CLI（服务必须兼容 Anthropic Messages）。
3. 选择 API Key，填写 HTTPS Base URL、模型和 Key。
4. 保存后点击“启用”。
5. 下一条新分析任务自动使用新线路。

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
python -m app.workers.analysis.agent_cli status
python -m app.workers.analysis.agent_cli doctor
```

依次确认：活动 Profile 存在、CLI 可执行、登录有效、FFmpeg/FFprobe 可执行、PostgreSQL/RabbitMQ/MinIO 地址对宿主机可达。Agent 状态未确认不会阻止 API 接收任务；任务会保持 `queued`，直到 Agent 恢复并消费消息。

若 `doctor` 返回 MinIO readiness probe 缺失，先执行 `docker compose -f docker-compose-env.yml run --rm minio-init`，由环境初始化任务幂等创建 `video-artifacts` bucket 与 `system/analysis-readiness-v1` 探针。若返回凭据无法读取，再由宿主机 MinIO 管理员确认统一 AK/SK 的 bucket 读取权限，并检查 `.env` 或 `.env.prod` 中唯一的 `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`。

### 本机登录不可用

系统服务必须与执行登录命令的用户一致。不要把用户登录文件复制到 Docker。重新登录后重启 Agent 服务，或重新执行 `install` 更新服务定义。

### API Key Provider 失败

确认协议与引擎匹配：Codex 只支持 Responses；Claude 要求 Anthropic Messages 语义。Base URL 通常是服务根或 `/v1` 根，不要填写完整的单次请求路径。Key 不会显示在日志中；必要时在管理页覆盖写入新 Key。

### 卸载

```text
uv run python -m app.workers.analysis.agent_cli uninstall
```

卸载只移除当前项目创建的用户服务定义，不删除数据库 Profile、CLI 登录态、视频制品或报告。
