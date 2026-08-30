# 026 Flutter 原生认证契约设计

- 状态：Accepted
- 日期：2026-08-30

## 1. 目标

为 Flutter iOS/Android 客户端提供不依赖浏览器 Cookie 或 WebView 的原生认证契约，同时复用现有账户、Argon2 密码哈希、JWT 签发、Refresh Session 轮换与撤销事实。

## 2. API 边界

原生认证使用 `/api/app/v1/auth/*`：

- `POST /register`：邮箱、用户名、密码注册并签发原生会话。
- `POST /login`：邮箱、密码登录并签发原生会话。
- `POST /refresh`：使用 Refresh Credential 单次轮换 Access/Refresh Credential。
- `GET /me`：使用 `Authorization: Bearer <access-token>` 查询当前用户。
- `POST /logout`：撤销提交的 Refresh Credential；客户端无论响应如何都清除本地会话。

浏览器 `/api/auth/*` 的 HttpOnly Cookie 行为保持不变。现有受保护业务 API 同时接受浏览器 Access Cookie 或原生 Bearer Access Token；请求显式携带无效 Bearer 时必须直接 401，不得回退到浏览器 Cookie。

## 3. Credential 生命周期

- Access Token 为短期 JWT，只保存在 Flutter 进程内存。
- Refresh Credential 为可轮换 JWT，原文仅返回给原生客户端并进入 Keychain/Keystore；服务端数据库只保存 HMAC 摘要。
- 每次 refresh 原子替换旧 Session；旧 Refresh Credential 重放必须失败。
- logout 撤销当前 Refresh Session。用户禁用、密码或权限变更继续由服务端账户事实控制。
- API 响应包含 Access/Refresh 到期时间，客户端不得解析 JWT 决定生命周期。

## 4. OpenAPI 与错误

- 所有操作提供稳定 operationId、严格请求模型和统一 Problem Details 错误。
- Bearer Security Scheme 进入 OpenAPI；Flutter 只消费排除管理端和 Cookie 登录接口的 App 专用冻结快照。
- 登录失败保持通用 `invalid_credentials`，不得泄露邮箱是否存在。
- 注册、登录与 refresh 继续使用既有速率限制和请求大小限制。

## 5. 非目标

本阶段不实现第三方 OAuth、短信验证码、多设备管理 UI、找回密码、WebView Cookie 迁移或 Provider 会话下发。
