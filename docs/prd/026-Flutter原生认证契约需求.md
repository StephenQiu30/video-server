# 026 Flutter 原生认证契约需求

- 状态：Accepted
- 日期：2026-08-30

## 用户目标

移动端用户可以注册、登录、恢复会话和退出，并使用同一账户访问受保护业务 API，而不需要浏览器 Cookie 或 WebView。

## 验收条件

- AC-026-01：注册与登录返回用户、Bearer Access Token、Refresh Credential 及两个到期时间，响应不设置认证 Cookie。
- AC-026-02：Bearer Access Token 可以访问 `/api/app/v1/auth/me` 与既有受保护业务接口。
- AC-026-03：Refresh Credential 每次使用后轮换，旧值重放返回 401。
- AC-026-04：退出撤销 Refresh Session，已撤销值不能再次刷新。
- AC-026-05：浏览器 Cookie 登录、恢复与退出行为不回归。
- AC-026-06：OpenAPI 提供稳定 operationId、Bearer Security Scheme 与严格模型，App 快照不包含管理端接口。
- AC-026-07：后端格式、类型、测试与 OpenAPI 契约门禁通过，Web 登录注册再经 agent-browser 验收。
