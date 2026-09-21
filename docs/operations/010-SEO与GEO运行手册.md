# SEO 与 GEO 运行手册

## 部署选择

个人、本地、Tailnet、预览与内部团队实例保持 `SITE_INDEXABLE=false`。只有计划公开介绍项目的正式网站才设置 `SITE_INDEXABLE=true`，并将 `SITE_URL` 设置为该网站的稳定 HTTPS origin。不要使用 localhost、IP 临时入口或 Tailnet 名称作为公开官网。

两个值都需要在构建和运行时保持一致。根 Compose 已将它们传给 frontend 的 build args 与 environment；前端 Dockerfile 默认不开启索引。本次不修改已有 `.env` / `.env.prod`，不自动发布服务。

准备公开时，使用现有部署流程重建 frontend 并重新创建容器。域名变更同样需要重建，不能只 restart。规范域名、HTTP 到 HTTPS 的重定向由部署入口维护；metadata 不替代入口跳转。`skipTrailingSlashRedirect` 为 API 保留，公开指南 canonical 固定为 `/guide/`。

## 公开部署后的检查

1. 无 Cookie 请求 `/`：HTTP 200，head 中 title、description、canonical、robots 正确；删除脚本后仍有产品说明和问答。检查 Cache-Control，不能在 CDN 将按 Cookie 返回的首页缓存为所有用户共享。
2. 请求 `/guide/`：唯一 h1、稳定目录锚点、面包屑、独立 description/canonical 与正文一致。首页与页脚应有真实可抓取链接。
3. 分别用普通 UA、Googlebot、bingbot 与 OAI-SearchBot 请求页面，正文应一致。不要只通过 UA 放行而忽略 CDN、WAF、IP 验证和网络可达性。
4. `/robots.txt` 中 API/health 保持禁止；`/sitemap.xml` 只包含正式 origin 的 `/` 和 `/guide/`。不要添加账户、任务、媒体文件、带 token 的短时链接或登录页面。
5. `/user/login/`、`/history/`、`/account/` 和带会话 Cookie 的 `/` 应 noindex。已有页面下线索引时允许爬虫读到 noindex；robots.txt 不能代替鉴权或搜索移除申请。
6. `/opengraph-image/` 返回 1200×630 PNG，分享标题与页面一致。通过 Schema Markup Validator 检查实体结构，通过 Google Rich Results Test 检查支持的类型；不是每个有效 schema 都有富结果资格。
7. 用 Search Console 与 Bing Webmaster Tools 验证正式域名并提交 sitemap，查看 URL 检查抓取后的 HTML。检查 Search Console 中站点是否允许纳入生成式 AI 功能，并使用其 Generative AI performance report 衡量表现。需要域名所有权及对应站长账户，不能把本地测试写成已提交或已收录。
8. 在桌面与 390px、明暗主题检查指南导航、问答阅读、CTA、焦点和横向溢出。Core Web Vitals 使用正式站真实用户数据判断，本地计时仅供排查。

## GitHub 可发现性

两个仓库的中英文根 README 提供产品定义、能力与费用边界、工作流、FAQ 和相互链接。本轮读取 GitHub 当前设置：两个仓库均已有 description，且各使用了 20 个 topics；不再堆叠同义关键词。Homepage 均为空，没有经过确认的公开产品域名，因此不填入本地或私有部署地址。

已更新并回读确认的主仓库 About 文案：

> 帧取 FrameFetch：开源自托管视频解析、剧本处理与 AI 视频分析，支持 Markdown/DOCX 报告导出。Self-hosted video parsing, screenplay processing and AI analysis.

已更新并回读确认的 App About 文案：

> 帧取 FrameFetch App：连接自托管 video-server 的 Flutter iOS/Android 客户端，支持素材上传、任务跟踪与 AI 分析结果阅读。Open-source mobile client for FrameFetch.

两个仓库的 About 已写入 GitHub；现有 topics 保持不变。正式域名确认后由维护者设置 Homepage，并上传合适的 social preview；README 发布必须走正常 Git 推送，不能把本地改动视为 GitHub 已更新。

## 持续衡量

上线时记录基线，此后按周比较相同时间窗口：品牌词（帧取、FrameFetch）与需求词（自托管视频分析、视频分镜分析、剧本文档分析）的曝光、点击、CTR、落地页和索引覆盖；记录从公开页面到部署文档、源码、注册入口的访问。项目目前没有为此新增第三方追踪器。

对生成式搜索记录固定问题、日期、地区/语言、搜索产品、是否引用项目、引用 URL 和描述是否准确。观察的是引用和事实正确率，不能把一次回答、未带引用的品牌提及或 robots 放行当作稳定排名提升。GitHub 使用仓库 Traffic 的访客与来源数据，注意其可见时间窗口。

## 本地验证记录

2026-09-21：

- 前端 `pnpm lint`、`pnpm format:check`、`pnpm test` 通过，67 个测试文件、331 项测试。测试覆盖匿名 SSR、access/refresh/自定义 Cookie、FAQ 与 JSON-LD 一致性、私有/公开索引配置和指南导航。
- 公开配置 `SITE_INDEXABLE=true`、占位测试域名 `https://framefetch.example` 的生产构建通过；在本机 8139 使用 standalone 输出验证，未部署到正式 8101 服务。
- 默认私有配置 `SITE_INDEXABLE=false` 的生产构建通过；standalone 原始响应中首页与指南均 noindex 且有正文，robots 不发布 sitemap，sitemap 无 URL。
- 普通 UA、Googlebot、bingbot、OAI-SearchBot 共 28 组页面/会话请求通过：head 中 robots/canonical 正确，匿名正文直接可读，带会话首页不输出公开 JSON-LD，且响应禁止公共缓存。
- robots、两页 sitemap 与 1200×630 PNG 分享图响应通过；占位域名仅用于本地配置测试，未进行 DNS、搜索提交或公网发布。
- Chromium 实测 1440px/390px、浅色/深色的首页和指南无横向溢出；目录、指南返回 FAQ 与跳至主要内容的焦点行为通过。两页 `#main-content` 的 axe-core 4.12.1 检查均为 0 项违规；这是局部自动检查，不代表完整 WCAG 认证。
- 两份业务 Compose 使用已有配置执行 `config --quiet` 通过；本次修改的 Markdown 本地文件链接目标存在，`git diff --check` 通过。
- GitHub 两仓 About 已更新并回读确认，topics 未改动，Homepage 继续为空。README 改动仍需正常推送后才在 GitHub 生效。

正式域名、站长账户、实际抓取/收录、线上 Core Web Vitals、真实 AI 引用与搜索表现尚未验收；用户明确本轮仅优化代码与 GitHub。
