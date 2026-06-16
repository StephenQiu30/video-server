# Proposal: 视频源可下载能力审计与中心化治理

## Problem Statement

当前项目存在两个视频源适配器中心：
1. `app.sources` 提供 `SourceAdapterRegistry` 和 `ParseService`（新中心）
2. `app.services.download_adapter` 保留独立 `PlatformAdapter`、`AdapterRegistry`、`DownloadEngineAdapter`（旧中心）

这种双中心架构导致：
- Agent Review 无法确认"支持"是否等于"可下载交付"
- 平台画像列表缺少下载交付级支持矩阵
- 测试可能依赖旧中心判断平台支持，产生误导

## Proposed Solution

1. **治理旧适配器中心**：将 `download_adapter.py` 中有价值的逻辑迁移到 `app.sources`，删除或废弃旧的 `PlatformAdapter`、`AdapterRegistry`、`DownloadEngineAdapter`
2. **建立支持矩阵**：定义 `supported_download`、`parse_only_or_unverified`、`fallback_attempt` 三级状态
3. **补充链路级测试**：为 B 站、YouTube、未知公网 fallback 提供下载链路级测试证据
4. **架构边界约束**：确保生产代码只从 `app.sources` 进入

## Success Criteria

- 项目只有一个视频源 adapter/registry 中心
- 支持矩阵明确列出每个平台的状态和验证证据
- 至少 B 站、YouTube、未知公网 fallback 有下载链路级测试
- 国内短视频平台有受限/风控失败语义测试
- Agent Review 能确认"支持"等于可下载交付
