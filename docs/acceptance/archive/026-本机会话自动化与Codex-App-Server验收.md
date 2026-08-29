# 026 本机会话自动化与 Codex App Server 验收

- 状态：Passed
- 日期：2026-08-29

## 自动化检查

- [x] Session Broker 单元测试通过。
- [x] 启动与 Provider 隔离契约测试通过。
- [x] Codex App Server 协议客户端单元测试通过。
- [x] `uv run ruff check app tests` 通过。
- [x] `uv run mypy app` 通过，463 个源文件无错误。
- [x] `uv run pytest` 通过，1080 项测试全部通过。
- [x] 本机 Codex App Server 真实结构化输出冒烟通过。
- [x] 视频号 Broker 冷重启后自动恢复 `ready`，不要求重新复制 Cookie。
- [x] 视频号固定公开样例的 metadata canary 通过。
- [x] 视频号固定公开样例的 media 下载、封装与清理 canary 通过。
- [x] 开发与生产 Compose 配置、启动 Shell 语法及 `git diff --check` 通过。

## 人工边界确认

- [x] 普通运行说明不再要求手工导出、复制或粘贴 Cookie。
- [x] 平台强制二维码/MFA 时只提示官方身份确认，不声称可绕过。
- [x] Codex 调用不监听网络端口、不保留持久 thread、不遗留子进程。
