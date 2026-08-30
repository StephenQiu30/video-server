# 026 Flutter 原生认证契约验收

- 状态：Passed
- 日期：2026-08-30

- [x] 原生注册、登录、Bearer `/me`、Refresh 轮换和退出撤销通过真实后端集成测试。
- [x] 无效 Bearer 不回退 Cookie；浏览器 Cookie 流程保持通过。
- [x] 原生认证响应不设置 Cookie，Refresh 原文不进入数据库或普通日志。
- [x] App 专用 OpenAPI 快照排除管理接口和浏览器 Cookie 登录接口。
- [x] 后端格式、静态类型、测试与 OpenAPI 门禁通过。
- [x] agent-browser 完成 Web 注册、登录、账户、退出与移动视口回归，无开放 P0/P1/P2。

最终结论：通过。后端 Ruff、Mypy（481 个源码文件）和 Pytest（1340 passed / 1 skipped）通过；Flutter iOS Simulator 真实调用原生认证接口完成注册、账户展示与退出。Web 端 196 项测试和生产构建通过；agent-browser 的桌面/390×844 回归发现 1 个 Low 排版问题，修复并复验后开放问题为 0。完整浏览器记录见 `qa-output/agent-browser-auth-20260830/report.md`。
