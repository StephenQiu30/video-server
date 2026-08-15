# 024 Native Runner 浏览器会话验收

- 状态：本机部署与自动化门禁通过；真实平台验收等待钥匙串授权
- 日期：2026-08-15

## 已验证

- [x] 浏览器会话不要求 Cookie 文件，命令只接收受限 browser specification。
- [x] 浏览器会话 Runner 强制使用 `presigned_put`，不能回退共享工作目录。
- [x] 预签名 URL origin 非 allowlist 时 fail closed。
- [x] Runner 返回对象 key 必须与 Worker 指定 key 完全一致。
- [x] Worker 重新下载并校验 SHA/大小/媒体元数据，再通过服务端 copy 晋升。
- [x] 下载失败、验证失败和完成后清理短时 delivery 对象。
- [x] Native 入口拒绝非 loopback bind。
- [x] YouTube/TikTok Native Runner 与固定 `1.3.1` PO Provider 由 launchd 常驻，三个 loopback 健康接口通过。
- [x] Docker API 容器可通过 `host.docker.internal` 访问两个 Native Runner。
- [x] 浏览器会话子进程继承宿主用户 HOME；匿名和文件 Cookie 子进程不继承。
- [x] launchd 运行时位于 Application Support，不要求 Desktop/完全磁盘访问权限。

## 待真实验收

- [ ] 专用 YouTube Profile + 原生 PO Provider 完整下载。
- [ ] 专用 TikTok Profile 完整下载。
- [ ] macOS Chrome Safe Storage 首次访问由账户持有人点击“始终允许”。
- [ ] Chrome 退出、Cookie 轮换、Profile 不存在和钥匙串拒绝。
- [ ] 预签名过期、MinIO 中断、Runner 取消和 Worker 重启恢复。
- [x] API、Runner/容器日志、DB、MinIO metadata、Outbox payload 和任务快照敏感 Cookie 标记扫描为零。
- [ ] RabbitMQ 在途消息正文的非消费式泄漏扫描。
- [ ] 通过真实 Artifact 继续完成视频分析与 MD/DOCX 报告。
