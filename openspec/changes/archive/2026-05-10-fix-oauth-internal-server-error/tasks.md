## 1. 认证路由优化

- [x] 1.1 在 `apps/api/app/routers/auth.py` 中为 GitHub API 请求添加 `User-Agent` 和 `Accept` 头部。
- [x] 1.2 引入 `response.raise_for_status()` 并在解析 JSON 前进行错误捕获。
- [x] 1.3 增加详细的日志记录，记录失败时的响应状态和内容摘要。

## 2. 验证与测试

- [x] 2.1 重启 Docker 容器以应用配置更改。
- [x] 2.2 在浏览器中重新执行 GitHub OAuth 登录流程，验证是否能成功登录并跳转。
- [x] 2.3 模拟 GitHub API 异常（如修改 Secret 导致 401），确认后端返回的是 400/401 而非 500。
