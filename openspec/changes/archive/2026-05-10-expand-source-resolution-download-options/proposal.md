# Expand Source Resolution Download Options

## Why

当前系统底层已经通过 yt-dlp 支持多种视频源，但前端和解析响应只暴露少量原始格式，用户无法稳定选择更低清晰度来减少下载体积和等待时间。抖音、小红书、TikTok 等视频源也需要按本地单用户 MVP 的边界明确为 yt-dlp best-effort 公公开视频支持，避免被误解为平台专用绕过能力。

## What Changes

- 解析响应增加来源识别信息，展示 yt-dlp 识别到的 extractor / source site。
- 解析结果优先生成推荐、最高 1080p、最高 720p、最高 480p、最高 360p 的清晰度预设。
- 清晰度预设使用简短 yt-dlp format selector，由现有任务 `format_id` 字段传给 Worker。
- 前端默认展示清晰度预设，不要求用户理解原始 format id。
- 合规 smoke 允许明确视频源名称出现在运行时代码中，但继续禁止 Cookie 托管、DRM / 付费墙 / 会员绕过和敏感日志泄露。
- 文档同步说明多视频源支持是 yt-dlp best-effort 能力，不承诺所有平台永久可用。

## Impact

- Affected specs: `video-download-tasks`
- Affected code: yt-dlp 适配层、API schema、前端解析结果展示、合规 smoke、后端测试、文档
