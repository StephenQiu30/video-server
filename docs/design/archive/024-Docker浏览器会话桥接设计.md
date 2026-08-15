# 024 Docker 浏览器会话桥接设计

交付状态：已验收归档。

## 决策

YouTube 与 TikTok 的下载执行进程继续由 Docker Compose 常驻，不在 macOS 上安装 launchd Runner。宿主机只执行一次性浏览器会话导出；导出结果按 Provider 过滤后，以只读目录挂载到单 Provider Operator Runner。

macOS Chrome Cookie 值由 Keychain 加密，Linux 容器无法仅靠挂载 Chrome Profile 解密。因此“复用浏览器”采用受控桥接，而不是把整个 Profile、Keychain 或浏览器调试端口暴露给容器。

```text
已登录 Chrome
    │ 一次性、按域过滤导出
    ▼
.provider-secrets/<provider>/<version>.cookies.txt (0400)
    │ Compose 只读挂载
    ▼
单 Provider Operator Runner ──固定代理出口──> YouTube / TikTok
    │ HMAC RPC + runner_work 共享卷
    ▼
API / Download Worker ──> MinIO
```

## 安全边界

- 导出器只接受登记的 Provider 与浏览器，不导出密码、Local Storage、历史记录或完整 Profile。
- Cookie 只保留 Provider Profile 的域名 allowlist，并要求存在平台登录 Cookie；目标目录拒绝 symlink，目录权限为 `0700`，文件权限为 `0400`。
- 每个 Operator Runner 只加载一个 Provider、并发为 1、Secret 只读；每次操作复制到 tmpfs 的 `0600` jar，操作结束即删除。
- API、Worker、日志、数据库、消息与制品中不出现 Cookie 值。普通用户不能上传 Cookie。
- YouTube 使用独立 PO Token sidecar；TikTok 使用每个部署独有且长期稳定的 19 位 device id，优先走官方 App extractor，再回退到受控网页挑战兼容层。
- Operator 模式继续拒绝 DRM、private、会员、付费与显式 `needs_auth` 内容；仅处理用户有权下载的内容。

## 运行拓扑

- `youtube-operator-runner`：只读挂载 YouTube Secret，并连接 `youtube-pot-provider`。
- `provider-operator-runner`：本期固定为 TikTok，只读挂载 TikTok Secret。
- `media-runner`：无 Cookie 匿名路径；Router 只在匿名验证失败时按 Provider key 回退。
- `worker-download`：与 Runner 共享 `runner_work:/work`，容器内 `RUNNER_WORKSPACE_ROOT` 必须固定为 `/work`，避免宿主机 `.env` 路径覆盖。

## 生命周期

Cookie 版本不可原地编辑。重新导出到新版本，更新 `*_COOKIE_VERSION` 后只重建对应 Operator Runner；旧版本仅在明确的回滚窗口内保留。出现账号告警、泄漏、权益漂移或平台规则变化时，从路由表移除 Provider、停止 Profile，并在平台侧撤销会话。
