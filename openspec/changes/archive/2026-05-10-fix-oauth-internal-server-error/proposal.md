## Why

目前 GitHub OAuth 登录流程在回调阶段（Callback）触发了 `Internal Server Error` (500)。通过日志分析发现，后端在解析 GitHub 用户资料响应时抛出了 `JSONDecodeError`，这通常是由于请求缺少必要的 Header（如 `User-Agent` 或 `Accept`）导致 GitHub 返回了 HTML 错误页面而非 JSON 数据。

## What Changes

- 在 GitHub OAuth 相关的所有 API 请求中增加标准 Header（`User-Agent`, `Accept`）。
- 增强 OAuth 回调逻辑的错误处理，在解析 JSON 前验证响应状态码及 Content-Type。
- 完善日志记录，捕获并记录第三方 API 返回的原始错误信息以便排查。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `user-auth`: 增强 OAuth 流程的健壮性和错误处理逻辑。

## Impact

- `apps/api/app/routers/auth.py`: 修改 GitHub 访问令牌交换和用户信息获取逻辑。
- GitHub 登录功能：修复后用户应能正常通过 GitHub 登录并跳转至工作台。
