## Context

当前系统使用自建的邮箱+密码体系。虽然功能完整，但在 MVP 阶段，维护一套安全的密码重置、验证邮件发送及加盐存储逻辑属于“过度设计”。GitHub OAuth 是开发者工具类产品最常用的方案，且能自动获取用户的公开 Profile 信息（头像、用户名等）。

## Goals / Non-Goals

**Goals:**
- 实现 GitHub OAuth2 授权码模式登录流程。
- 简化 `User` 模型，移除对密码复杂度的强依赖。
- 统一前后端的认证握手逻辑。
- 保持对现有 JWT 令牌系统的兼容。

**Non-Goals:**
- 不再支持邮箱密码注册（为了彻底简化，后续可根据需要通过第三方库如 FastAPI Users 重新找回）。
- 不实现多账号绑定逻辑。

## Decisions

### 1. 轻量级手动实现 OAuth 回调 vs. 引入 FastAPI Users
**选择：手动实现（配合 httpx）**
- **理由**：为了极致的“不过度设计”，手动实现一个 `/callback` 路由只需要约 20 行代码。相比之下，引入 FastAPI Users 会增加大量模型抽象和依赖包，增加系统复杂性。
- **替代方案**：FastAPI Users（过于繁重）、Authlib（略显复杂）。

### 2. 用户静默注册
**选择：登录即注册**
- **理由**：当用户通过 GitHub 授权返回后，如果数据库不存在该 GitHub UID 的用户，则直接创建。
- **流程**：`GitHub 授权` -> `后端获取 UID` -> `查询/创建 User` -> `发放本系统 JWT`。

### 3. 数据模型调整
- 新增 `github_id`: String (唯一索引)
- `password_hash`: 改为可选 (Nullable)

## Risks / Trade-offs

- **[Risk] GitHub API 网络波动** → **[Mitigation]** 设置合理的请求超时，并在前端展示友好的错误提示。
- **[Risk] 国内访问 GitHub 缓慢** → **[Mitigation]** 建议用户配置镜像或代理，或者作为 MVP 版本暂时接受此限制。
