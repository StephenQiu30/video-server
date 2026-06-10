---
change_id: worker-failure-classification
title: "Worker 失败分类补全：platform_restricted 与 platform_rate_limited"
status: implemented
related_plan: "docs/plans/05-Worker下载执行与失败分类计划.md"
related_prd: "docs/prd/03-异步下载任务主链路.md"
related_issue: STE-267
---

# Worker 失败分类补全

## 1. 背景

PLAN05 要求 Worker 对常见失败建立稳定分类。现有 `failure_code()` 已覆盖 6 种模式（format_unavailable、file_too_large、task_timeout、unsupported_platform、browser_cookies_unavailable、download_failed），但缺少 `platform_restricted` 和 `platform_rate_limited` 两种关键分类。

API 层 `download_adapter._classify_parse_error()` 已有完整分类，Worker 层需要保持语义一致。

## 2. 变更内容

### 2.1 `apps/worker/worker/failures.py`

- `failure_code()` 新增 `_is_platform_restricted()` 检测（login required、DRM、付费、地区限制等）
- `failure_code()` 新增 `_is_platform_rate_limited()` 检测（429、验证码、频率限制等）
- `format_failure_reason()` 对应新增中文提示
- 新增两个辅助函数：`_is_platform_restricted()` 和 `_is_platform_rate_limited()`

### 2.2 `apps/api/tests/test_worker_failure_classification.py`（新增）

- `TestFailureCodeClassification`：12 个 WorkerFailureCode 全量分类测试
- `TestRetryabilityMatrix`：完整重试矩阵测试
- `TestStageTracking`：失败阶段追踪测试
- `TestMarkFailedStagePropagation`：`_mark_failed` 函数直接测试
- `TestProcessDownloadTaskHappyPath`：完整 happy path 集成测试

## 3. 分类与重试矩阵

| 失败码 | 可重试 | 说明 |
| --- | --- | --- |
| `DOWNLOAD_FAILED` | ✅ | 网络错误等通用下载失败 |
| `STORAGE_FAILED` | ✅ | MinIO 上传失败 |
| `TASK_TIMEOUT` | ✅ | 下载超时 |
| `PLATFORM_RATE_LIMITED` | ✅ | 平台限流，稍后可重试 |
| `FORMAT_UNAVAILABLE` | ❌ | 格式不可用 |
| `FILE_TOO_LARGE` | ❌ | 文件超限 |
| `UNSUPPORTED_PLATFORM` | ❌ | 不支持的平台 |
| `BROWSER_COOKIES_UNAVAILABLE` | ❌ | Cookie 读取失败 |
| `PLATFORM_RESTRICTED` | ❌ | 登录/DRM/付费/地区限制 |
| `MEDIA_TOOLS_MISSING` | ❌ | FFmpeg 缺失 |
| `FFPROBE_FAILED` | ❌ | ffprobe 校验失败 |
| `TASK_CANCELED` | ❌ | 用户取消 |

## 4. 验证方式

```bash
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_worker_failure_classification.py -v
```

## 5. 风险

- 分类依赖异常消息文本匹配，第三方平台异常格式变化可能导致误分类
- `_is_platform_restricted` 的 "region" 标记可能有误匹配风险，但优先保证召回率
