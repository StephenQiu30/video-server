# Facebook 分享帖子解析调研

日期：2026-08-12

## 1. 现场结论

用户提交的 `https://www.facebook.com/share/p/1DDHArdZuy/` 在已登录的真实 Chrome 中最终解析为：

`https://www.facebook.com/groups/claudeaicommunity/permalink/1347155834118247/`

页面结构化数据中的唯一附件类型为 `Photo`，附件 id 为 `10168534459259466`；该帖子不包含视频。匿名 Runner 对分享地址和最终 permalink 都进入了 yt-dlp 的 Facebook extractor，但统一返回 `Cannot parse data`，导致 API 错误地暴露为通用 inspection 失败。

## 2. 上游证据

- 项目固定的 [Facebook extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/facebook.py) 支持 group permalink，但只提取 `Video`，不提供图片帖子下载语义。
- yt-dlp 的 [Facebook `Cannot parse data` issue #15161](https://github.com/yt-dlp/yt-dlp/issues/15161) 截至本次调研仍处于 open；其中确认部分视频页面需要浏览器 impersonation。
- 较早的分享 Reel 报告 [issue #12846](https://github.com/yt-dlp/yt-dlp/issues/12846) 已被标记为 #15161 的 duplicate，说明单纯把 `/share/*` 改写成另一种 Facebook URL 不能消除 extractor 回归。
- yt-dlp 官方 [插件机制](https://github.com/yt-dlp/yt-dlp/wiki/Plugins) 允许项目在内置 extractor 前执行受控的入口识别，然后把确认的单视频 id 委托回内置 Facebook extractor。

## 3. 修复策略

新增仅匹配 Facebook `/share/p/` 与 group `posts/permalink` 的入口 extractor：

1. 跟随分享跳转后重新校验最终 host 与帖子 id，禁止跨域和身份变化。
2. 只读取 Facebook 页面中的第一方 `data-sjs` 结构化附件数据。
3. 恰好一个 `Video` 时，以 `facebook:{video_id}` 委托给固定版本的官方 extractor。
4. `Photo` 或多个附件立即返回 `provider_media_unsupported`，不再伪装成 Provider 故障。
5. 附件 schema 无法识别，或官方 Facebook extractor 仍返回 `Cannot parse data` 时，归类为 `extractor_regression`，不进行无意义的 inspection 重试。
6. Facebook Profile 固定使用已批准的 Chrome impersonation；登录墙仍沿用独立的 operator-managed 会话边界。

## 4. 产品边界

当前产品只处理单视频。图片、相册和多附件帖子不会下载，也不会静默选择第一项。API 对这类输入返回 HTTP 422，并明确说明“提交的链接不包含一个受支持的视频”。这与 `docs/design/017-其他短视频平台分阶段接入设计.md` 中的 fail-closed 多资产边界一致。

## 5. 验证

- 用户真实分享链接：新 extractor 明确识别为图片帖并返回稳定的 media unsupported 错误。
- 单视频结构样本：委托结果固定为官方 `Facebook` extractor 与绑定的视频 id。
- 负例：跨域跳转、帖子 id 变化、图片、多附件和未知 schema 全部 fail closed。
- 后端全量测试、mypy、Ruff、前端 lint/typecheck/Vitest 与 Next.js production build 均通过。
