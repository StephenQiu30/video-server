## Why

当前系统的登录注册功能采用传统的邮箱/密码模式，这引入了密码找回、邮箱验证等复杂的工程量（过度设计）。为了遵循“极简”与“不重复造轮子”的原则，引入 GitHub OAuth 认证可以大幅简化代码逻辑，提升安全性，并利用 GitHub 的成熟生态减少运维负担。

## What Changes

- **认证模式变更**：引入 GitHub OAuth 登录作为首选或唯一登录方式，取代/简化现有的手动注册流程。
- **用户模型精简**：移除或隐藏对密码哈希的强制依赖，转而存储 GitHub UID 和 Profile 信息。
- **前端适配**：在登录页面增加“GitHub 登录”按钮，移除复杂的注册表单。
- **后端回调**：新增 `/api/auth/callback/github` 路由，处理 OAuth 握手并自动静默注册/登录。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `user-auth`: 增加对 OAuth2 三方授权登录的要求，简化凭据校验逻辑。

## Impact

- **后端**：`apps/api/app/routers/auth.py` (核心逻辑变更), `app/models.py` (用户模型调整), `app/core/config.py` (新增 GitHub Client ID/Secret 配置)。
- **前端**：`apps/web/src/pages/Auth.tsx` (UI 简化), `lib/api.ts` (登录态处理优化)。
- **配置**：根目录 `.env` 需要新增 GitHub OAuth 凭据。
