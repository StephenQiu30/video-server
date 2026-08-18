# 固定 Provider 探针运行手册

本手册用于当前固定引擎、Runner 拓扑和网络出口的回归诊断。公开诊断样本只定位
Extractor、访问和下载链路问题；生产发布仍必须使用项目自有或明确授权、由 Secret
配置的 canary，并完成完整视频分析证据。

## 1. 前置检查

当 `.env` 配置 Provider Operator 时，先启动对应浏览器桥接与 Compose
Profile：

```bash
./scripts/provider-cookie-bridge.sh youtube start
./scripts/provider-cookie-bridge.sh tiktok start
./scripts/provider-cookie-bridge.sh douyin start
./scripts/provider-cookie-bridge.sh xiaohongshu start
./scripts/provider-cookie-bridge.sh reddit start

docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator --profile provider-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator up -d --build

curl --fail http://127.0.0.1:8101/health/ready
```

就绪检查会探测匿名 Runner 和所有配置的 Operator Runner。`provider-canary` 必须
显示 `runner_work:/work` 挂载，且容器内 `RUNNER_WORKSPACE_ROOT=/work`。

## 2. 固定矩阵

样本位于 `backend/app/workers/canary/fixed_public_cases.json`。每个 Registry key
必须恰好有同一 target/version 的 metadata 与 media 两条记录；URL 不会出现在命令
输出或数据库 canary 行中。

```bash
docker exec video-provider-canary \
  python -m app.workers.canary.fixed_matrix --stage metadata

docker exec video-provider-canary \
  python -m app.workers.canary.fixed_matrix --stage media
```

只复测单个平台：

```bash
docker exec video-provider-canary \
  python -m app.workers.canary.fixed_matrix --provider youtube --stage media
```

只有本次选择的所有目标都成功时命令返回 0；任何失败返回 1，并写入正常
`provider_canary_results`。不要用 `|| true` 掩盖发布门禁。

## 3. 结果判读

| 稳定错误 | 判定 |
| --- | --- |
| `provider_auth_required` / `provider_session_expired` | 会话缺失或失效；先检查桥接与 Operator，不轮换账号放大请求 |
| `provider_verification_failed` | 平台人机验证/挑战未通过；保留最后有效登录态并降级平台，不自动规避 CAPTCHA |
| `format_unavailable` | 相邻 rendition 漂移或原规格消失；探针有界重检三次，用户重试自动选择当前兼容规格 |
| `provider_drm_protected` / `provider_content_restricted` | 内容能力边界，不重试、不绕过 |
| `extractor_regression` / `provider_temporarily_unavailable` | 上游页面或固定 extractor 回归，降级对应平台 |
| `provider_rate_limited` | 当前会话/出口限流，停止高频复测并等待 |
| `media_validation_failed` | 下载文件、共享路径或 ffprobe 契约异常，属于本项目公共链路故障 |

metadata 成功不等于可下载；media 成功也不等于 AI 分析完整。平台恢复为 verified
仍需要近期 metadata、media、完整视频 Analysis attestation 和状态恢复迟滞。

2026-08-18 在当前固定引擎、出口和会话下，metadata 22/22、media 22/22 均通过。
小红书固定样本必须使用官方分享/Feed 生成且携带 `xsec_token` 的完整 URL；不得把
缺少 token 的旧裸 URL 当作当前有效样本。Tumblr 由项目可信插件读取当前 `www`
公开页，避免 yt-dlp 旧 blog 子域路径的 429。

## 4. 更新固定样本

只在原内容删除、链接写错或不再属于预期能力边界时升级 target 版本。更新前先用
当前 Runner 验证 Provider identity、单视频边界、最低规格完整下载、SHA-256 和
ffprobe；同一版本不得静默换 URL。测试要求矩阵和 Registry 双向一致，新增/删除
Provider 时必须同步更新。
