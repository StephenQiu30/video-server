# Simplify Ant Pro Download UI

## Why

当前 M1 仍应优先服务“粘贴链接 -> 解析 -> 创建任务 -> 查看状态 -> 下载文件”的本机下载闭环。前端不应呈现复杂 SaaS 首页、营销型说明页或自定义装饰视觉，而应回到 Ant Design Pro 原生蓝白工具页。

本变更继续承接已有 `simplify-ant-pro-download-ui`，不再新建重复的前端 UI OpenSpec 变更。

## What Changes

- `/` 和 `/workspace` 共用同一个下载器页面，打开首页即可使用工具。
- 页面流程参考鱼皮 `free-video-downloader` 的 MVP 思路：链接输入、解析结果、推荐格式、创建任务、任务状态和下载入口。
- 页面配色收敛到 Ant Design Pro 默认蓝白风格，不强行改写成功、警告、错误语义色。
- 成功任务改为原生轻量文字展示，不再使用大块绿色或自定义成功面板。
- 合规说明不再作为前端主导航页面，避免下载工具主流程被说明页分散。
- 不改后端 API、下载任务、Worker、存储、B 站下载逻辑和本机 Chrome 登录态读取策略。
- 不引入登录、支付、AI 总结、SEO 页面、批量任务、平台专用解析或 Cookie 托管。

## Impact

- Affected specs: `web-download-workspace`
- Affected code: 前端首页、工作台、任务历史、全局样式和少量验收文档
