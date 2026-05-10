# Support Local Bilibili Download Flow

## Why

当前 B 站链接在工作台解析时会触发 API 500，用户只能看到 `Failed to fetch`。真实根因是 `yt-dlp` 已经解析出 B 站元数据，但返回的浮点时长不符合当前响应模型。修复该问题后，还需要补齐本机单用户 Worker 读取 Chrome 登录态的能力，才能更接近桌面下载器体验，把用户自己能观看的 B 站内容下载成功。

## What Changes

- 修复 B 站解析响应字段兼容，避免浮点时长、文件大小等字段导致 500。
- 解析结果优先提供“推荐下载”格式，使用 `bestvideo+bestaudio/best`。
- 允许本机 Worker 通过配置读取 Chrome 登录态，但不上传、不保存、不入库 Cookie。
- 调整一键启动：Docker API/Web + 本机 Worker 后台进程，支持 PID、日志、重复启动和停止。
- 更新合规脚本和文档，将该能力限定为本机单用户例外，不扩展为公网 SaaS Cookie 托管。

## Impact

- Affected specs: `video-download-tasks`, `project-runtime-foundation`
- Affected code: yt-dlp 适配层、Worker 下载选项、启动脚本、合规 smoke、B 站 smoke、前端错误提示、文档和 ADR
