# Security Policy

## 产品边界

本项目只处理用户有权下载和分析的公开、非 DRM HTTP(S) 内容。不得在普通业务请求中提交账号凭据、Cookie、私网 URL，或使用本项目规避访问控制、版权保护和平台授权。005 允许运维在独立 Runner 中为 allowlist Provider 配置最小权益会话；该能力不允许 private、会员、购买或 DRM 内容。

## 强制控制

- 生产环境必须替换 `.env.prod.example` 中的全部占位凭据；配置校验会拒绝开发密钥。
- 匿名 Media Runner 不得获得 Provider Secret；凭据 Runner 只能获得对应 Provider 的版本化只读 Secret。所有 Runner 均不得获得 PostgreSQL、RabbitMQ、MinIO、Valkey 或 AI provider 凭据，也不得挂载 Docker socket。
- 用户 URL 只加密持久化；普通日志、消息和 API 错误中不得出现完整 URL query。
- 外部媒体流量只能经过 egress proxy；入口校验不是 SSRF 防线的替代品。
- `POST /api/inspections` 等普通 JSON 接口不接受原始 Cookie；受控 Cookie 只能通过 005 运维 Secret 生命周期进入凭据 Runner。任意 yt-dlp 参数、shell 命令、输出路径或文件名模板始终不接受。

## 报告漏洞

请不要在公开 Issue 中披露可利用细节、密钥或用户内容。通过仓库所有者提供的私有安全报告渠道提交复现条件、影响范围和最小 PoC；维护者完成分级和修复后再协调披露。

## 发布门禁

涉及 URL、Runner、子进程、对象存储、会话、队列或模型输入的变更，必须包含对应的滥用/失败测试，并通过 `AGENTS.md` 规定的全部质量门禁。
