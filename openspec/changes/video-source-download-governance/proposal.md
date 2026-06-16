## Why

当前代码已有 `app.sources`、`SourceAdapterRegistry` 和 `ParseService`，但旧 `app.services.download_adapter` 仍保留另一套 `PlatformAdapter`、`AdapterRegistry` 和 `DownloadEngineAdapter`，形成双中心并存。同时平台画像列表容易被误读为"已支持下载平台"，项目缺少"支持=可下载交付"的统一口径和验收标准。本次变更以 PRD09 为需求源，约束支持矩阵、下载交付证据和 adapter/registry 单中心规则。

## What Changes

- 定义视频源支持口径：只有同时满足解析、任务创建、Worker 下载、产物校验和对象存储交付的来源，才算 `supported_download`。
- 定义三种支持状态：`supported_download`、`parse_only_or_unverified`、`fallback_attempt`。
- 要求视频源接入以 `app.sources` 为唯一中心，旧 `app.services.download_adapter` 不再作为并行 registry 中心。
- 建立支持矩阵文档，要求每个平台必须有下载链路验收证据。

## Capabilities

### New Capabilities

- `video-source-download-governance`: 定义视频源可下载支持口径、三种支持状态、支持矩阵要求和中心化架构约束。
- `download-support-matrix`: 定义支持矩阵必须包含的字段（platform_id、host、adapter、download_engine、required_auth、known_limits、validation_evidence）和状态判定规则。

### Modified Capabilities

- `video-source-adapter`: 旧 `app.services.download_adapter` 中仍有价值的 response conversion 和错误分类应迁移到 `app.sources`，旧中心应被删除或降级为 deprecated shim。
- `source-adapter-registry`: 明确 `app.sources` 下的 `SourceAdapterRegistry` 是唯一注册中心，不允许保留并行 registry。

## Impact

- **新增文档**: `docs/prd/09-视频源可下载能力与中心化架构.md`（已存在）
- **新增计划**: `docs/plans/14-视频源可下载能力审计与中心化治理计划.md`（已存在）
- **索引更新**: `docs/prd/README.md` 和 `docs/README.md`（已完成）
- **新增 OpenSpec change**: `openspec/changes/video-source-download-governance/`
- **下游影响**: 代码治理任务将由后续 PLAN14 子任务执行
- **依赖**: 无新增外部依赖
