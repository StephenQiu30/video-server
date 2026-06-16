# Design: 视频源可下载能力审计与中心化治理

## 架构变更

### 1. 治理旧适配器中心

**当前状态**：
- `app.sources.registry.SourceAdapterRegistry` - 新中心
- `app.services.download_adapter.AdapterRegistry` - 旧中心
- `app.services.download_adapter.DownloadEngineAdapter` - 旧中心包装器

**目标状态**：
- 只保留 `app.sources.registry.SourceAdapterRegistry`
- 将 `download_adapter.py` 中有价值的逻辑迁移到 `app.sources.models` 或 `app.sources.adapters.ytdlp`
- 删除或废弃旧的 `PlatformAdapter`、`AdapterRegistry`、`DownloadEngineAdapter`

**迁移策略**：
1. `_to_parse_response()` 中的格式转换逻辑已迁移到 `app.sources.models.source_info_to_parse_response()`
2. `_classify_parse_error()` 中的错误分类逻辑已迁移到各适配器的 `map_error()` 方法
3. `_build_resolution_presets()` 中的分辨率预设逻辑已迁移到 `app.sources.models`
4. 水印提示逻辑已迁移到 `app.sources.models`

### 2. 建立支持矩阵

**文档位置**：`docs/acceptance/02-视频源可下载支持矩阵.md`

**矩阵结构**：
- platform_id: 平台标识
- host: 平台域名
- adapter: 适配器类名
- download_engine: 下载引擎
- required_auth: 是否需要认证
- known_limits: 已知限制
- validation_evidence: 验证证据
- support_status: 支持状态

### 3. 下载链路测试

**测试策略**：
1. B 站：公开 BV URL 解析 -> 任务创建 -> Worker fake download -> 对象存储链路
2. YouTube：公开测试 URL 解析 -> format selector -> Worker fake download
3. 未知公网 fallback：安全 host 校验通过 -> unsupported 映射正确
4. 国内短视频：平台识别 -> 受限/风控失败语义

**Fake Integration 证据**：
- 使用 mock 替代真实网络请求
- 验证 format_id 传递契约
- 验证失败分类语义

## 文件变更清单

### 新增文件
- `openspec/changes/video-source-download-governance/` (OpenSpec change)
- `docs/acceptance/02-视频源可下载支持矩阵.md` (支持矩阵)
- `apps/api/tests/test_download_chain.py` (下载链路测试)

### 修改文件
- `apps/api/tests/test_architecture_boundaries.py` (增加架构边界约束)
- `apps/api/tests/test_download_adapter.py` (更新测试引用)
- `apps/api/tests/test_platform_adapters.py` (更新测试引用)

### 删除文件
- 无（保留旧代码但标记为 deprecated，避免破坏现有依赖）

## 验证方式

1. 自动化测试：pytest 验证所有测试通过
2. 架构边界测试：断言 `app.services.download_adapter` 不再定义独立 adapter/registry 中心
3. 支持矩阵文档：人工审查每个平台的状态和证据
4. Agent Review：确认"支持"等于可下载交付
