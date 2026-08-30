# 026 Flutter 原生认证契约计划

- 状态：Ready
- 日期：2026-08-30

1. [ ] 先增加原生注册、Bearer 查询、轮换重放与退出撤销集成测试。
2. [ ] 扩展 SessionGrant 到期时间并增加严格原生会话 schema。
3. [ ] 增加 `/api/app/v1/auth/*` 路由，并让受保护业务依赖安全接受 Bearer。
4. [ ] 扩展 OpenAPI 契约测试并导出 App 专用冻结快照。
5. [ ] 运行后端格式、类型、测试与浏览器 Cookie 回归。
6. [ ] 使用 agent-browser 复验 Web 注册、登录、账户与退出流程。
