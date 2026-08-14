# 文档归档路线与技术债清单

- 状态：Active
- 更新日期：2026-08-14

## 1. 归档目标

所有编号化交付最终都必须形成 `Design → PRD → Plan → Acceptance` 四件套，四份状态分别达到 `Accepted / Accepted / Complete(d) / Accepted` 后通过受保护命令归档。`research/` 记录仍有效的外部事实，`operations/` 记录当前运行方式；它们需要持续更新，不应为了“目录为空”而归档。

## 2. 已识别的历史技术债

| 编号 | 技术债 | 本轮处理 |
| --- | --- | --- |
| 002 | 已通过的 MVP 被后续 Provider、故障注入和全站视觉扩展重复阻断 | 收敛原始范围，扩展任务分别转交 005、006、009 后归档 |
| 016 | 实现与真实验收已完成，但缺 PRD 和 Plan，状态仍停在 Phase 1/Passed | 补齐四件套、同步 Accepted/Completed 后归档 |
| 018 | RabbitMQ 可靠性已经实现，但只有 Design | 按现有代码、测试与提交证据补齐 PRD/Plan/Acceptance 后归档 |
| 021 | 封面持久化已经实现，但只有未入索引的 Design | 补齐索引和四件套后归档 |

历史技术债只允许依据现有实现、测试和真实验收证据补齐，不得用“代码看起来存在”直接把 Pending 改成 Accepted。

## 3. 仍需真实交付的编号

| 优先级 | 编号 | 未归档原因 | 达到归档还需要完成 |
| --- | --- | --- | --- |
| P0 | 009 | 全站方案 3 已实现，但 Acceptance 仍缺完整当前证据 | 完成桌面/390px 跨路由数据、空、错、加载态；键盘、焦点、明暗主题、200% 缩放、reduced motion、axe；同源生产镜像与完整门禁，并回填 Acceptance |
| P0 | 004 | 下载历史代码完成，缺真实 PostgreSQL/MinIO 与浏览器数据态证据 | 验证 owner 隔离、分页/筛选/搜索、过期 inspection、文件入口和方案 3 响应式；同步 Plan/Acceptance 为完成态 |
| P0 | 008 | 业务与权限 A1–A5 已通过，A6–A7 是当前 UI/门禁缺口 | 完成资料/用户管理桌面与移动浏览器回归、全量前后端门禁和 Compose 解析 |
| P0 | 011 | 管理分析实现存在，但验收仍是模板 | 构造多用户/多来源/六状态/UTC 样本；核对 PostgreSQL 聚合、权限、OpenAPI、7/30/90 日页面、空错态、可访问性和全量门禁 |
| P0 | 022 | 核心实现和 Windows Codex 已通过，跨 Provider/平台证据不足 | 用真实 API Key Profile 完成脱敏视频分析；在 macOS、Linux 验证 install/restart/status/uninstall；回填安全与运行证据 |
| P1 | 010 | Codex 已通过，但原需求明确包含 Claude | 在可用 Claude 模型路由上完成同一授权视频的完整视觉 E2E，或通过新的产品决策正式移除 Claude 首期承诺；不能仅改状态绕过 |
| P1 | 005 | Phase 1 代码部分完成，生产会话与 canary 证据仍不完整，Phase 2 也在同一范围 | 完成 YouTube 授权 Cookie/POT/固定出口、真实 canary、审计和供应链门禁；对用户 ProviderCredential/多媒体 Phase 2 实施或拆为新编号后重新冻结 005 范围 |
| P1 | 017 | 代码门禁存在但 `acceptance: pending`，实际完整视频分析证明不足 | 提供授权样本，完成下载→Agent→PostgreSQL→MinIO MD/DOCX→WebSocket→浏览器/CI 证据；所有纳入归档的平台为 verified 后改 marker 并运行专用命令 |
| P2 | 006 | Public Beta/Stable v1 伞形需求跨越多个已归档子项，仍含真实生产能力缺口 | 在 PRD 中标记已由 012–015、018、020 等交付的需求；完成剩余网络隔离、滥用防护、配额、备份恢复、可观测性、发布治理、音频/字幕/批量，或拆分成独立编号后收敛 006 |
| P2 | 019 | 需求和设计完成，但代码明确未实施且依赖设备/授权输入 | 依次完成浏览器原始媒体导入、设备配对/签名/撤销、Edge Import、视频号元宝/Windows Adapter、红果 Android Adapter、SBOM/许可证与真实三阶段 canary |

## 4. 执行顺序

1. 先完成 009 的统一视觉与浏览器证据，解除 004、008、011 的公共阻断。
2. 使用同一真实 Compose 和浏览器环境依次关闭 004、008、011，避免重复搭建验收数据。
3. 完成 022 的 API Key/macOS/Linux 验收，再决定 010 Claude 的可用环境或产品范围。
4. 收敛 005 与 017 的 Provider 范围；不要让未实施 Phase 2 永久阻断已完成 Phase 1，应通过新编号承接明确延期范围。
5. 将 006 拆解为可独立验收的生产能力编号；019 在获得设备、授权样本和发行输入后实施。

每关闭一个编号，先执行 `python scripts/archive_completed_docs.py`，确认只出现预期编号，再执行 `--apply`；017 始终使用其 Provider/Acceptance 双门禁专用命令。
