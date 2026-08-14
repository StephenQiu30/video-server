# 022 跨平台 AI 分析 Agent 与模型 Provider 配置验收

- 状态：内部实现与自动化契约已通过；真实 API Key、macOS、Linux 实机待验
- 日期：2026-08-14

## 1. 自动化门禁

- [x] `cd backend && uv run pytest`
- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm test`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run openapi:check`

## 2. Provider 管理

- [x] 管理员可查看默认 `local-codex`，非管理员返回 403。
- [x] 可新增 Codex API Key Profile，GET 响应只有 `credential_configured=true`。
- [x] 可新增 Claude API Key Profile。
- [x] 公网 HTTP、带用户名密码/query/fragment 的 URL 被拒绝。
- [x] 编辑 Key 留空保留原密文，填写新 Key 后密文变化。
- [x] 启用新 Profile 后旧 Profile 原子失活，始终最多一个活动项。
- [x] 活动 Profile 不可删除；非活动 Profile 删除后密文一并移除。

## 3. Agent 与执行

- [x] `doctor` 输出当前 Provider、模型、CLI 版本与存储就绪状态且不输出 Key。
- [x] 本机 Codex 登录无需 Key，完成一条真实分析。
- [ ] API Key Profile 完成一条真实分析，结果记录正确的 Provider key 与模型。
- [x] 活动 Profile 切换后无需重启 API/Agent，下一个任务使用新线路。
- [x] Agent 停止超过 stale window 后管理页显示离线，创建分析返回不可用。
- [x] Agent 恢复后心跳自动恢复，创建分析重新可用。

## 4. 跨平台常驻

- [x] Windows 安装后创建当前用户计划任务，登录启动，异常退出后重启。
- [ ] macOS 安装后创建 LaunchAgent，登录启动，异常退出后重启。
- [ ] Linux 安装后创建 systemd user unit，登录启动，异常退出后重启。
- [ ] `status` 能反映服务状态，`uninstall` 只移除本项目服务定义。

## 5. 安全与界面

- [x] 数据库没有明文 Key，密文不能绑定到另一个 Profile key 解密。
- [ ] API、任务结果、Agent 普通日志和进程参数中没有 Key。
- [x] 项目没有修改用户 `auth.json/config.toml/.claude`。
- [x] 390×844 可完成新增、编辑与启用，无横向滚动、遮挡或不可达按钮。
- [x] 页面明确区分 Agent 在线、当前线路、认证方式和模型。

## 6. 2026-08-13 实测证据

| 项目 | 结果 |
| --- | --- |
| 后端 | Ruff、Mypy 通过；`601 passed, 1 skipped` |
| 前端 | lint、format、119 项测试、Next 生产构建通过 |
| Windows Agent | 计划任务 `FrameFetchAnalysisAgent` 为 Running；`doctor` 输出 `provider=local-codex`、`codex-cli 0.145.0`、`storage=ready` |
| 心跳 | `analysis_worker_heartbeats` 持续更新，恢复后管理页显示 Agent 在线 |
| 真实分析 | 任务 `dbe0b221-7631-4a0d-8bef-047017784588` 的第 2 次运行成功；`provider=local-codex`、`model=gpt-5.6-sol`、`cli_version=codex-cli 0.145.0` |
| 浏览器 | 桌面与 390×844 通过；无横向溢出，API Key 弹窗可滚动到底部，移动导航入口与 Escape 关闭可用 |

## 7. 2026-08-14 自动化补证

| 验收项 | 证据 |
| --- | --- |
| Key 更新语义 | `test_api_key_update_preserves_blank_and_rotates_new_secret` 验证留空时密文不变、填写新 Key 后密文轮换且可正确解密。 |
| API 脱敏 | 管理接口 CRUD 集成测试验证创建、查询和更新响应均不包含 `api_key` 或原始 Secret。 |
| Profile 热切换 | `test_updated_active_profile_rebuilds_adapter_for_next_task` 验证同一 Agent 进程按 `updated_at` 失效缓存，下一任务使用更新后的模型、Endpoint 与 Key。 |
| stale fail-closed | Worker Registry 测试验证心跳超时后不可用；创建分析测试验证没有兼容 Worker 时在持久化前返回不可用。 |
| 进程参数隔离 | Runtime 测试验证 API Key 仅进入受控子进程环境，不进入命令参数。 |
| 服务命令契约 | Windows、macOS、Linux 的 `status` 命令均有自动化覆盖；Windows install/uninstall 验证只操作本项目任务和定义文件。macOS/Linux 实机生命周期仍是外部门禁。 |

本轮定向门禁为 Ruff 通过、`23 passed`。安全条目仍保持未勾选，因为真实 API Key 执行的 Agent 普通日志、任务结果与进程快照还没有可审计样本；跨平台常驻条目也必须由对应操作系统实机证明，不能用命令生成测试替代。
