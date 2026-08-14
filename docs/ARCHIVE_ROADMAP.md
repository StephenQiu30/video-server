# 文档归档路线与技术债清单

- 状态：Active
- 更新日期：2026-08-14

## 1. 归档目标

所有编号化交付最终都必须形成 `Design → PRD → Plan → Acceptance` 四件套，四份状态分别达到 `Accepted / Accepted / Complete(d) / Accepted` 后通过受保护命令按类型归档到 `design/archive/`、`prd/archive/`、`plans/archive/`、`acceptance/archive/`，不使用集中式 `archive/<编号>/`。`research/` 记录仍有效的外部事实，`operations/` 记录当前运行方式；它们需要持续更新，不应为了“目录为空”而归档。

## 2. 已识别的历史技术债

| 编号 | 技术债 | 本轮处理 |
| --- | --- | --- |
| 002 | 已通过的 MVP 被后续 Provider、故障注入和全站视觉扩展重复阻断 | 收敛原始范围，扩展任务分别转交 005、006、009 后归档 |
| 004 | 实现和自动化已完成，但验收仍保留早期真实依赖/浏览器待办，且引用了过时的 72px Header | 用当前 Compose、桌面/移动浏览器、历史数据态记录和全绿 CI 复验，统一为 80px 当前视觉真值后归档 |
| 008 | A1–A5 已通过，但 Plan 仍引用已删除的 ProTable，A6–A7 状态未随方案 3 QA 同步 | 修正为 Next.js + shadcn/Radix 当前实现，补普通用户权限、桌面/移动与运行边界证据后归档 |
| 009 | 多轮 `design-qa.md` 已通过，但 Acceptance 的 74 项清单与工程/axe 证据长期未回填；Windows 统一 CI 入口无法解析 `npm.cmd` | 补做全路由 axe，修复 warning Badge 4.15:1 对比度和跨平台 npm 解析；统一镜像、12 路由桌面/移动复扫和 CI 通过后归档 |
| 011 | 聚合实现、测试和真实数据已存在，但 Acceptance 仍是未执行模板 | 用 PostgreSQL 当前事实核对 7/30/90 日、14 来源、权限、响应式、axe 和 CI 后归档 |
| 016 | 实现与真实验收已完成，但缺 PRD 和 Plan，状态仍停在 Phase 1/Passed | 补齐四件套、同步 Accepted/Completed 后归档 |
| 018 | RabbitMQ 可靠性已经实现，但只有 Design | 按现有代码、测试与提交证据补齐 PRD/Plan/Acceptance 后归档 |
| 021 | 封面持久化已经实现，但只有未入索引的 Design | 补齐索引和四件套后归档 |

历史技术债只允许依据现有实现、测试和真实验收证据补齐，不得用“代码看起来存在”直接把 Pending 改成 Accepted。

## 3. 仍需真实交付的编号

| 优先级 | 编号 | 未归档原因 | 达到归档还需要完成 |
| --- | --- | --- | --- |
| P0 | 023 | Phase A 当前态契约、旧数据回填、feature flag 与 OpenAPI 基线已完成；上传基础设施、Document 聚合和剧本 Skill 尚未实施 | 完成 multipart/quarantine/Import Worker、本地 MP4 → Artifact → 视频拉片、五种剧本文档解析、剧本分析、中英双向改写、Skill 供应链、安全负例和桌面/移动真实 E2E |
| P0 | 022 | 内部实现、Key 轮换/脱敏、Profile 热切换、stale fail-closed 和三平台命令契约已补证；缺少外部执行环境 | 用真实 API Key Profile 完成脱敏视频分析并审计日志/结果/进程；在 macOS、Linux 实机验证 install/restart/status/uninstall |
| P1 | 010 | Codex 已通过，但原需求明确包含 Claude；2026-08-14 复验又确认当前 Windows 会话未启用 Claude 沙箱 feature gate，CLI 按策略拒绝启动 | 在启用 Claude Windows 沙箱的会话或其他受支持隔离环境完成同一授权视频的完整视觉 E2E，继续完成队列级持久化、安全 fixture 与孤儿进程验收；或通过新的产品决策正式移除 Claude 首期承诺，不能仅改状态绕过 |
| P1 | 005 | Phase 1 代码部分完成，生产会话与 canary 证据仍不完整，Phase 2 也在同一范围 | 完成 YouTube 授权 Cookie/POT/固定出口、真实 canary、审计和供应链门禁；对用户 ProviderCredential/多媒体 Phase 2 实施或拆为新编号后重新冻结 005 范围 |
| P1 | 017 | 代码门禁存在但 `acceptance: pending`，实际完整视频分析证明不足 | 提供授权样本，完成下载→Agent→PostgreSQL→MinIO MD/DOCX→WebSocket→浏览器/CI 证据；所有纳入归档的平台为 verified 后改 marker 并运行专用命令 |
| P2 | 006 | Public Beta/Stable v1 伞形需求跨越多个已归档子项，仍含真实生产能力缺口 | 在 PRD 中标记已由 012–015、018、020 等交付的需求；完成剩余网络隔离、滥用防护、配额、备份恢复、可观测性、发布治理、音频/字幕/批量，或拆分成独立编号后收敛 006 |
| P2 | 019 | 已把浏览器上传基础转交 023；设备协议和平台 Adapter 仍未实施且依赖设备/授权输入 | 先等待 023 Accepted，再完成设备配对/签名/撤销、Edge Import、视频号元宝/Windows Adapter、红果 Android Adapter、SBOM/许可证与真实三阶段 canary |

## 4. 执行顺序

1. 004、008、009、011 已使用同一真实 Compose、独立权限会话、桌面/移动浏览器和 CI 证据关闭并归档。
2. 实施 023，先独立关闭浏览器 MP4 上传，再完成剧本文档、三个 Skill 和中英双向改写；023 Accepted 后 019 才进入 Edge 协议实施。
3. 完成 022 的 API Key/macOS/Linux 验收，再决定 010 Claude 的可用环境或产品范围。
4. 收敛 005 与 017 的 Provider 范围；不要让未实施 Phase 2 永久阻断已完成 Phase 1，应通过新编号承接明确延期范围。
5. 将 006 拆解为可独立验收的生产能力编号；019 在 023 Accepted 且获得设备、授权样本和发行输入后实施。

每关闭一个编号，先执行 `python scripts/archive_completed_docs.py`，确认只出现预期编号，再执行 `--apply`；017 始终使用其 Provider/Acceptance 双门禁专用命令。
