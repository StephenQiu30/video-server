# 024 Native Runner 浏览器会话需求

- 状态：Phase 1 implemented；production acceptance pending
- 日期：2026-08-15

## 必须满足

1. 用户继续通过现有链接解析入口创建任务，不手动下载或上传。
2. 登录态只能在用户宿主机读取，不进入 Docker、API、数据库或日志。
3. 一个 Native Runner 只能绑定一个允许受控会话的 Provider，并发为一。
4. Native Runner 不获得数据库、RabbitMQ、MinIO、Valkey 或 AI 长期凭据。
5. 制品使用短时、固定对象 key 的一次性上传授权交付；Runner 不能选择任意目标。
6. Worker 必须在无 Provider 凭据的环境重新读取、计算 SHA-256、验证文件边界后晋升。
7. 会话过期、平台验证、上传失败、对象冲突与媒体验证失败必须保持稳定错误语义。
8. Native 服务默认只监听 `127.0.0.1`/`::1`，容器通过 `host.docker.internal` 访问。

## 非目标

- 不支持 private、会员、购买、DRM 或地域权益扩张。
- 不把日常主浏览器 Profile 作为推荐生产账号。
- 不承诺平台反自动化规则变化后无需升级 yt-dlp、PO Provider 或 Profile。
