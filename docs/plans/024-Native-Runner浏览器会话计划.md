# 024 Native Runner 浏览器会话计划

- 状态：Phase 1 已部署；平台 E2E 等待一次性钥匙串授权
- 日期：2026-08-15

## 阶段

1. 已完成：浏览器 Profile 会话配置、Provider/并发/transport 门禁。
2. 已完成：Runner 下载请求可携带固定对象的预签名 PUT。
3. 已完成：Worker 重新下载隔离对象、验证并服务端晋升。
4. 已完成：loopback Native Runner 入口、环境模板与运行手册。
5. 已完成：YouTube/TikTok Native Runner 与 YouTube PO 服务安装为用户级 launchd 常驻进程；运行时放在 `~/Library/Application Support/帧取/native-runner`，避免给后台进程授予 Desktop 或完全磁盘访问权限。
6. 已完成：修复浏览器会话子进程 HOME 隔离冲突；只有 `BrowserCookieSession` 使用宿主用户 HOME，匿名 Runner 和 Cookie 文件 Runner 仍使用任务工作目录。
7. 待完成：账户持有人在 macOS 钥匙串对 Chrome Safe Storage 完成一次“始终允许”，随后执行 YouTube/TikTok metadata、完整下载、ffprobe、SHA、MinIO 和分析 E2E。
8. 待完成：根据真实下载结果补充会话过期 UI、版本更新通道与发布证据。
