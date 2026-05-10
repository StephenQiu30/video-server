# Design

## Decisions

- B 站能力以“本机单用户下载器”为定位，不作为公网 SaaS 能力。
- 继续使用 `yt-dlp` 通用适配层，不引入 yutto、DownKyi 或自研 B 站解析。
- Cookie 读取只发生在本机 Worker 进程内，通过 `YTDLP_COOKIES_FROM_BROWSER=chrome` 控制，默认不通过 API 或前端传递。
- 默认一键启动保留 Docker API/Web，同时启动本机 Worker，以便 Worker 访问 Chrome 登录态、FFmpeg 和本地临时目录。
- 前端和 API 必须把 B 站解析失败、Cookie 不可读、Worker 未运行等问题转成中文可诊断原因。

## Non-Goals

- 不做 DRM 破解、付费绕过、批量盗采、AI 总结、支付或会员系统。
- 不把 Cookie 保存到数据库、对象存储、日志或前端状态。
- 不承诺 B 站所有会员、高码率、番剧、课程都能下载；若用户账号不可访问，必须明确失败原因。
