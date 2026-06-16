# 设计：视频源可下载能力与中心化架构

## 1. 目标

以 PRD09 为需求源，建立视频源可下载支持的统一口径和中心化架构约束。

## 2. 非目标

1. 不实现代码改动（代码治理由 PLAN14 子任务执行）。
2. 不绕过平台限制。
3. 不承诺 `yt-dlp` 全量 extractor 都是正式支持平台。

## 3. 数据契约

### 3.1 支持状态枚举

```python
class DownloadSupportStatus(str, Enum):
    SUPPORTED_DOWNLOAD = "supported_download"
    PARSE_ONLY_OR_UNVERIFIED = "parse_only_or_unverified"
    FALLBACK_ATTEMPT = "fallback_attempt"
```

### 3.2 支持矩阵字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| platform_id | str | 是 | 平台稳定唯一标识 |
| host | str | 是 | 支持的主域名 |
| adapter | str | 是 | 适配器类名 |
| download_engine | str | 是 | 下载引擎 |
| required_auth | str | 是 | 认证要求 |
| known_limits | list[str] | 是 | 已知限制 |
| validation_evidence | str | 是 | 验收证据 |
| support_status | DownloadSupportStatus | 是 | 支持状态 |

## 4. 状态流

```text
URL 输入
  ↓
安全校验 + 平台画像识别
  ↓
┌─ 匹配平台画像 → 专用适配器 → parse → format → task → worker download → 验证 → 对象存储 → 交付
│   (supported_download 或 parse_only_or_unverified，取决于是否有验收证据)
│
└─ 未匹配 → YtDlpAdapter fallback → parse → format → task → worker download → 验证 → 对象存储 → 交付
    (fallback_attempt，成功则升级为 parse_only_or_unverified)
```

## 5. 失败路径

1. 平台限制 → `platform_restricted`
2. 风控/限流 → `platform_rate_limited`
3. 不支持的平台 → `unsupported_platform`
4. 格式不可用 → `format_unavailable`
5. 下载失败 → `download_failed`

## 6. 权限边界

1. 不绕过 DRM、付费墙、会员、登录态、版权或地区限制。
2. 不承诺 `yt-dlp` 所有 extractor 都是项目正式支持平台。
3. 不把"平台可识别"误写为"平台可下载"。

## 7. 迁移/回滚影响

1. 本次变更仅涉及文档和 OpenSpec artifacts，无代码改动。
2. 代码治理任务由 PLAN14 子任务执行，有独立的迁移和回滚计划。
3. 如果 PRD09 需要回滚，只需删除文档和索引条目。

## 8. 验证方式

1. PRD09 文档存在且内容完整。
2. 索引文件已更新。
3. OpenSpec artifacts 已创建。
4. `bash scripts/validate-repository.sh` 通过。
5. `git diff --check` 无问题。
