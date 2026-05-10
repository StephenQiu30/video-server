## Context

GitHub OAuth 回调接口在某些环境下返回了 HTML 错误页（如 403 Forbidden 或 401 Unauthorized），导致后端尝试解析 JSON 时抛出 `JSONDecodeError`。主要原因是在使用 `httpx` 进行服务器间请求时，未遵循 GitHub API 的规范：
1. 缺少 `User-Agent` Header（GitHub API 强制要求）。
2. 缺少 `Accept: application/json` Header，导致在错误情况下可能返回 HTML。

## Goals / Non-Goals

**Goals:**
- 修复 GitHub OAuth 回调导致的 500 错误。
- 增加请求头规范性。
- 增加对 GitHub 响应的健壮性验证。

**Non-Goals:**
- 不改变现有的 OAuth 逻辑流程。
- 不引入新的第三方认证库。

## Decisions

### 1. 统一添加 User-Agent 和 Accept 头部
所有发往 `github.com` 的请求都将携带：
- `User-Agent`: `StephenVideo-API`
- `Accept`: `application/json`

### 2. 在解析 JSON 前验证 Content-Type 和 Status Code
使用 `response.raise_for_status()` 替代直接解析，并捕获 `JSONDecodeError` 以返回更有意义的错误信息。

## Risks / Trade-offs

- [Risk] GitHub API 变更 → [Mitigation] 增加详细的 Error Log，包括状态码和响应体片段，便于快速定位。
