# 024 Docker 浏览器会话桥接需求

交付状态：已验收归档。

## 目标

在不运行宿主机常驻下载服务的前提下，让 Docker 内的 YouTube、TikTok Runner 安全复用运维浏览器登录态，并完成解析、下载、校验与对象存储闭环。

## 功能需求

1. 运维可从已登录的 Chrome、Chromium 或 Firefox 一次性导出 YouTube/TikTok 会话。
2. 导出文件必须按 Provider 域过滤、验证必要登录 Cookie、原子写入并收紧权限。
3. Compose 必须提供相互隔离的 YouTube 与 TikTok Operator Runner，Cookie 目录只读挂载且不暴露宿主机端口。
4. YouTube 必须使用受控 PO Token sidecar；TikTok 必须使用稳定 device id 与项目内 WAF 兼容 extractor。
5. API 与 Download Worker 必须通过 HMAC 内部 RPC 路由到 Operator Runner；Worker 必须能通过共享卷读取并校验 Runner 制品。
6. 会话轮换必须使用新版本并可单独重建平台 Runner，不依赖 launchd 或宿主机后台进程。

## 非目标

- 不挂载或复制完整浏览器 Profile、Keychain、密码与 2FA 数据。
- 不开放 Chrome 远程调试端口，不让容器控制日常浏览器。
- 不支持 DRM、private、好友可见、会员、购买/租赁或地域绕过内容。
- 不承诺 Cookie 永久有效；平台会话仍需按告警和 canary 轮换。

## 验收指标

- 两个平台均返回 `operator_managed` 与当前 Cookie version。
- 两个平台均完成真实音视频下载，Worker 可见制品且 SHA-256 一致。
- TikTok 连续解析可通过稳定 device id 避免单纯网页 WAF 抖动。
- Compose 开发/生产配置解析成功，Cookie 内容不进入 Git 与日志。
