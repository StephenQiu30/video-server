# Backend Production Parser Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将 `video-server` 后端升级为可上线的万能视频下载器服务：在保持账号、配额、任务、对象存储、Worker 既有能力的前提下，增强 B 站与国内短视频平台解析能力，补齐平台画像、错误分类、合规边界、上线防护与可验证测试。

**Architecture:** 后端继续采用 FastAPI API + SQLAlchemy 数据模型 + RQ Worker + yt-dlp 下载内核 + 对象存储的前后端分离架构。解析层从“少量适配器 + fallback”升级为“平台画像注册表 + 平台适配器 + 统一错误分类 + 解析响应扩展”的边界层，任务层只消费规范化 URL 和格式选择，不绕过平台权限限制。

**Tech Stack:** Python 3.14, FastAPI, Pydantic, SQLAlchemy, RQ, Redis, PostgreSQL, MinIO/S3, yt-dlp, pytest, Docker Compose.

---

## Current Backend Audit

- 已具备：登录鉴权、GitHub OAuth、`/api/auth/me`、任务归属校验、日配额、并发配额、存储配额、任务重试、任务事件、过期清理、对象存储预签名下载、Docker 部署入口、本机启动入口。
- 已具备：`BilibiliAdapter`、`DomesticShortVideoAdapter`、`YtDlpAdapter` 三层解析适配器，以及 URL 分享文本提取。
- 主要缺口：国内平台域名覆盖不完整，解析响应没有机器可读平台信息，错误码过粗，yt-dlp 失败原因没有统一分类，合规高风险内容缺少前置拒绝语义，解析能力没有平台矩阵文档和上线验收脚本闭环。

## Non-Goals

- 不绕过 DRM、会员、登录态、付费墙、地区限制、平台风控和版权保护。
- 不新增前端代码，本阶段只优化 `video-server`。
- 不引入用户 Cookie 托管、批量爬取、站外内容分发、转码农场或支付系统。
- 不在测试中依赖真实平台网络作为默认单元测试；真实平台只放入手动 smoke 测试说明。

## Milestone M2 Issue Slices

### M2-01 test: 平台画像与 URL 归一化红灯测试

- [x] 新增 `apps/api/tests/test_platform_profiles.py`。
- [x] 写入 `test_platform_profile_matches_mainland_short_video_hosts()`：
  - 输入 `https://www.douyin.com/video/123` 断言平台 id 为 `douyin`、展示名为 `抖音`、类别为 `domestic_short_video`。
  - 输入 `https://www.kuaishou.com/short-video/abc` 断言平台 id 为 `kuaishou`。
  - 输入 `https://www.xiaohongshu.com/explore/abc` 断言平台 id 为 `xiaohongshu`。
  - 输入 `https://www.ixigua.com/123` 断言平台 id 为 `ixigua`。
  - 输入 `https://m.weibo.cn/status/123` 断言平台 id 为 `weibo`。
- [x] 写入 `test_platform_profile_matches_bilibili_short_hosts()`：
  - 输入 `https://b23.tv/abc`、`https://m.bilibili.com/video/BV1xx411c7mD`、`https://www.bilibili.com/video/BV1xx411c7mD`，断言平台 id 均为 `bilibili`。
- [x] 写入 `test_platform_profile_marks_known_public_fallback_hosts()`：
  - 输入 `https://youtu.be/abc`、`https://www.youtube.com/watch?v=abc`、`https://www.tiktok.com/@u/video/123`，断言平台 id 分别为 `youtube`、`youtube`、`tiktok`。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_platform_profiles.py`，确认失败，失败点应指向缺少平台画像能力。

### M2-02 impl: 平台画像注册表与解析响应扩展

- [x] 新增 `apps/api/app/services/platforms.py`。
- [x] 定义 `PlatformProfile` dataclass：
  - 字段：`id: str`、`display_name: str`、`category: str`、`hosts: tuple[str, ...]`、`requires_public_access: bool = True`、`supports_public_parse: bool = True`、`compliance_note: str | None = None`。
- [x] 定义 `PLATFORM_PROFILES`：
  - `bilibili`: `bilibili.com`, `b23.tv`
  - `douyin`: `douyin.com`, `iesdouyin.com`
  - `kuaishou`: `kuaishou.com`
  - `xiaohongshu`: `xiaohongshu.com`, `xhslink.com`
  - `ixigua`: `ixigua.com`
  - `weibo`: `weibo.com`, `weibo.cn`
  - `tiktok`: `tiktok.com`
  - `youtube`: `youtube.com`, `youtu.be`, `youtube-nocookie.com`
  - `vimeo`: `vimeo.com`
  - `dailymotion`: `dailymotion.com`, `dai.ly`
- [x] 实现 `find_platform_profile(url: str) -> PlatformProfile | None`：
  - 使用 `urlparse(url).hostname`。
  - host 完全匹配或子域名匹配均可命中。
  - 空 host 返回 `None`。
- [x] 在 `apps/api/app/schemas.py` 中为 `ParseResponse` 添加向后兼容字段：
  - `platform_id: str | None = None`
  - `platform_category: str | None = None`
  - `compliance_note: str | None = None`
- [x] 在 `apps/api/app/services/download_adapter.py` 的 `_to_parse_response()` 中调用 `find_platform_profile(url)`，填充新增字段；`source_site` 优先使用平台画像展示名，找不到时保留原 yt-dlp extractor 映射。
- [x] 更新 `DomesticShortVideoAdapter.supports()` 和 `BilibiliAdapter.supports()` 使用平台画像或补齐 host 列表，确保测试域名命中专用适配器。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_platform_profiles.py apps/api/tests/test_download_adapter.py apps/api/tests/test_platform_adapters.py`，确认通过。

### M2-03 test: 解析错误分类红灯测试

- [x] 新增 `apps/api/tests/test_parse_error_classification.py`。
- [x] 写入 `test_classifies_login_required_as_platform_restricted()`，构造异常文本 `Login required`，断言错误码 `platform_restricted`、HTTP 403。
- [x] 写入 `test_classifies_drm_and_paid_content_as_platform_restricted()`，构造异常文本 `DRM protected content` 和 `premium only`，断言错误码 `platform_restricted`。
- [x] 写入 `test_classifies_rate_limit_as_platform_rate_limited()`，构造异常文本 `HTTP Error 429: Too Many Requests`，断言错误码 `platform_rate_limited`、HTTP 429。
- [x] 写入 `test_classifies_unsupported_url_as_unsupported_platform()`，构造异常文本 `Unsupported URL`，断言错误码 `unsupported_platform`、HTTP 422。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_parse_error_classification.py`，确认失败。

### M2-04 impl: 统一 yt-dlp 错误分类与合规文案

- [x] 在 `apps/api/app/services/download_adapter.py` 中新增 `_classify_parse_error(exc: Exception, platform_name: str | None = None) -> AppError`。
- [x] 错误映射：
  - 登录、私有、会员、付费、版权、DRM、地区限制：`platform_restricted`, 403。
  - 平台限流、验证码、Too Many Requests、429：`platform_rate_limited`, 429。
  - Unsupported URL、No suitable extractor：`unsupported_platform`, 422。
  - 连接超时、读取超时、temporary failure：`platform_unavailable`, 503。
  - 其他：`parse_failed`, 422。
- [x] `YtDlpAdapter.map_parse_error()`、`BilibiliAdapter.map_parse_error()` 统一调用 `_classify_parse_error()`，B 站可传入 `B 站` 用于更准确中文提示。
- [x] `_extract_with_ytdlp()` 捕获 `DownloadError` 时保留原始异常链，不直接吞成固定 `parse_failed`，让适配器层分类。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_parse_error_classification.py apps/api/tests/test_platform_adapters.py`，确认通过。

### M2-05 test: API 解析契约与认证边界红灯测试

- [x] 在 `apps/api/tests/test_api_contract.py` 或新文件中新增 `test_parse_response_includes_platform_metadata()`。
- [x] 使用 monkeypatch 替换 `_extract_with_ytdlp()`，通过登录用户调用 `POST /api/parse`，断言响应包含：
  - `platform_id`
  - `platform_category`
  - `compliance_note`
  - `formats`
- [x] 新增 `test_parse_requires_authenticated_user()`，未带 token 调用 `/api/parse` 应返回 401。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_api_contract.py`，确认新增平台字段相关测试先失败。

### M2-06 impl: API 解析契约稳定化

- [x] 保持 `/api/parse` 入参只接收 `url`，不引入前端破坏性参数。
- [x] 确保 `ParseResponse` 新增字段都有默认值，旧前端可继续读取 `source_site` 和 `formats`。
- [x] 对平台画像命中的内容返回统一 `compliance_note`：
  - 默认文案：`仅支持公开可访问内容；不支持 DRM、会员、付费或需登录内容。`
  - 国内短视频文案：`仅支持公开视频链接；平台风控、私密作品、登录态内容和付费内容不会绕过。`
  - B 站文案：`仅支持公开视频；番剧、会员、付费、版权受限或需登录内容不会绕过。`
- [x] 运行 `npm test`，确认全量测试通过。

### M2-07 test: 任务创建前置平台校验红灯测试

- [x] 在 `apps/api/tests/test_task_endpoints.py` 新增 `test_create_task_rejects_unsupported_protocol_or_platform_before_enqueue()`。
- [x] 对 `POST /api/tasks` 输入 `https://example.invalid/video/1`，期望返回 `unsupported_platform` 或明确 `parse_failed` 之前的 422，且不调用队列 enqueue。
- [x] 对 `POST /api/tasks` 输入合法 B 站 URL，保留现有创建任务行为。
- [x] 运行相关测试，确认 unsupported 平台前置校验失败。

### M2-08 impl: 任务创建平台前置校验

- [x] 新增 `validate_supported_download_url(url: str) -> PlatformProfile | None`：
  - 命中已知平台返回画像。
  - 未命中但 yt-dlp fallback 允许的公共平台可返回 `None`，但必须在错误文档中说明 fallback 风险。
  - 对明显非视频站点和内网地址返回 `unsupported_platform` 或 `invalid_url`。
- [x] 在任务创建前执行 URL 归一化和平台校验，避免明显无效任务进入队列。
- [x] 不阻断 YouTube/Vimeo/Dailymotion 等已知公共平台 fallback。
- [x] 运行 `PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_task_endpoints.py apps/api/tests/test_url_normalization.py`。

### M2-09 docs: 后端平台能力矩阵与上线验收文档

- [x] 新增 `docs/03-架构设计/04-后端解析平台能力矩阵.md`：
  - 列出平台、域名、解析策略、上线状态、限制说明、测试策略。
- [x] 更新 `docs/05-测试验收/03-上线级SaaS验收标准.md`：
  - 增加平台画像字段验收。
  - 增加错误码验收。
  - 增加真实平台 smoke 测试必须手动执行且不得纳入默认 CI 的说明。
- [x] 更新 `docs/06-运维合规/02-风险与合规边界.md`：
  - 明确新增平台不代表绕过访问控制。
  - 明确平台风控、验证码、登录态内容的返回策略。

### M2-10 chore: 上线 smoke 脚本与验证闭环

- [x] 检查现有 `scripts/smoke_parse_samples.sh`，若不足则补充 `scripts/smoke_parse_platforms.sh`。
- [x] 脚本读取环境变量：
  - `API_BASE_URL`
  - `API_TOKEN`
  - `SMOKE_SAMPLE_FILE`
- [x] 默认不包含真实平台样例；提供 `docs/05-测试验收/smoke-platform-samples.example.json` 作为模板。
- [x] 脚本对每个样例调用 `/api/parse`，输出平台 id、格式数量、错误码。
- [x] 将脚本纳入文档，不纳入 `npm test` 默认执行。

## Execution Order

1. 先执行 M2-01 到 M2-02，补齐平台画像和解析响应字段。
2. 再执行 M2-03 到 M2-04，补齐错误分类。
3. 再执行 M2-05 到 M2-06，锁定 API 契约。
4. 再执行 M2-07 到 M2-08，补齐任务创建前置校验。
5. 最后执行 M2-09 到 M2-10，补齐文档和上线 smoke 验证。

## Verification Commands

```bash
npm test
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_platform_profiles.py
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_parse_error_classification.py
npm run docker:config
```

## Self-Review Notes

- 计划避免把“万能下载器”误做成“绕过平台限制”的工具，所有受限内容统一返回合规错误。
- 新增字段只做响应扩展，不破坏当前前端读取 `source_site`、`formats` 的兼容路径。
- 默认测试只使用 monkeypatch 和本地单元测试，不让 CI 依赖真实视频平台网络稳定性。
- 真实平台能力必须通过 smoke 样例手动验收，且样例文件不应提交私人链接、Cookie 或敏感内容。
