## Context

当前后端视频解析逻辑分散在两个模块中：
- `services/platforms.py`：定义 `PlatformProfile` 数据类和平台画像表（12 个平台），负责 URL → 平台识别。
- `services/download_adapter.py`：定义 `PlatformAdapter` 基类、三个具体适配器（`YtDlpAdapter`、`BilibiliAdapter`、`DomesticShortVideoAdapter`）、`AdapterRegistry` 和 `DownloadEngineAdapter`，负责解析和格式转换。

问题：
1. `PlatformAdapter` 不是正式协议——没有 ABC 约束，`supports()` 接收 `ParsedHost` 而非统一领域对象。
2. `AdapterRegistry` 硬编码默认适配器列表，无法动态注册。
3. `DownloadEngineAdapter` 同时承担解析和格式转换职责（`_to_parse_response`），违反单一职责。
4. 路由层直接调用 `DownloadEngineAdapter`，没有中间服务层。
5. 错误映射逻辑在 `_classify_parse_error()` 函数中，与适配器实现耦合。

## Goals / Non-Goals

**Goals:**
- 定义正式的视频源领域模型（`SourceRequest`、`SourceContext`、`SourceInfo`、`MediaVariant`、`SubtitleTrack`、`SourceCapability`）。
- 定义 `VideoSourceAdapter` ABC 协议，约束 `supports()`、`parse()`、`map_error()` 接口。
- 实现 `SourceAdapterRegistry` 支持动态注册、优先级选择和 fallback 链。
- 创建 `ParseService` 作为统一解析入口，隔离路由与适配器细节。
- 保持 `ParseResponse` API 契约 100% 向后兼容。
- 将适配器实现迁移到 `apps/api/app/sources/` 模块。

**Non-Goals:**
- 不改造 worker 下载链路（`download_runner.py` 继续直接使用 yt-dlp）。
- 不实现远程动态插件加载。
- 不为每个平台实现深度专有能力（如 Bilibili 弹幕、抖音直播）。
- 不改造 MinIO 存储归档链路。
- 不修改 `ParseResponse` schema 字段。

## Decisions

### Decision 1: 模块布局 — `sources/` 独立模块

**选择**: 在 `apps/api/app/sources/` 下创建独立模块，包含 `models.py`、`adapter.py`、`registry.py`、`adapters/` 子目录。

**替代方案**: 在现有 `services/download_adapter.py` 中重构。
**理由**: 独立模块更清晰地分离领域层（sources）和服务层（services），避免单文件膨胀。`services/` 保留业务服务（`parse_service.py`），`sources/` 专注视频源领域。

### Decision 2: 领域对象 — frozen dataclass

**选择**: 使用 `@dataclass(frozen=True)` 定义领域对象。
**替代方案**: Pydantic BaseModel。
**理由**: 领域对象不需要序列化/验证，frozen dataclass 更轻量、不可变，与现有 `PlatformProfile` 风格一致。

### Decision 3: 适配器协议 — ABC 而非 Protocol

**选择**: 使用 `abc.ABC` + `@abstractmethod` 定义 `VideoSourceAdapter`。
**替代方案**: `typing.Protocol`（结构化子类型）。
**理由**: ABC 提供运行时类型检查和明确的继承关系，与现有 `PlatformAdapter` 的命名约定模式一致但更严格。Protocol 更适合鸭子类型场景，但这里需要确保所有适配器实现完整的错误映射。

### Decision 4: 注册中心 — 有序列表 + 首匹配

**选择**: `SourceAdapterRegistry` 内部维护 `list[VideoSourceAdapter]`，`get_adapter()` 按顺序返回第一个 `supports()` 为 True 的适配器。
**替代方案**: 基于平台 ID 的 dict 映射。
**理由**: 有序列表支持 fallback 链语义（专用 → 通用），且不需要维护平台 ID → 适配器的映射表。新适配器只需 `register()` 即可插入链中。

### Decision 5: 错误映射 — 每个适配器自带 map_error()

**选择**: 每个适配器实现 `map_error()` 方法，`ParseService` 在捕获异常后调用。
**替代方案**: 集中式错误分类函数。
**理由**: 不同平台可能有不同的错误模式（如 Bilibili 的 "大会员" vs YouTube 的 "premium"），适配器可以针对性地扩展映射逻辑。基类提供默认实现，子类可覆盖。

### Decision 6: ParseService — 薄服务层

**选择**: `ParseService` 仅做 `SourceRequest 构建 → 注册中心选择 → 适配器解析 → SourceInfo → ParseResponse 转换` 的编排。
**替代方案**: 将格式转换逻辑（分辨率预设、watermark hint）也放入 ParseService。
**理由**: 格式转换逻辑与 yt-dlp 输出强耦合，放在 `sources/` 模块的转换函数中更内聚。ParseService 只负责编排。

### Decision 7: 向后兼容 — 渐进式迁移

**选择**: 先创建 `sources/` 模块和 `ParseService`，然后将 `routers/parse.py` 切换到 `ParseService`，最后标记旧 `DownloadEngineAdapter` 为 deprecated。
**替代方案**: 一次性替换所有引用。
**理由**: 渐进式迁移允许在每一步运行回归测试，降低引入 bug 的风险。旧模块保留到确认所有测试通过后再清理。

## Risks / Trade-offs

**[Risk] 适配器迁移引入回归** → 保留现有测试（`test_platform_adapters.py`、`test_download_adapter.py`、`test_platform_profiles.py`）作为回归门禁，迁移后必须全部通过。

**[Risk] SourceInfo → ParseResponse 转换丢失信息** → 转换函数复用现有 `_to_parse_response()` 核心逻辑，仅调整输入来源（从 raw dict 改为 SourceInfo）。

**[Risk] 新模块增加维护成本** → `sources/` 模块的职责边界清晰（领域层），后续新增适配器只需在 `adapters/` 下添加实现并注册，不需要改动核心逻辑。

## Migration Plan

1. 创建 `apps/api/app/sources/` 模块结构。
2. 实现领域对象和适配器协议（TDD）。
3. 实现注册中心（TDD）。
4. 将现有适配器迁移到新协议（TDD）。
5. 创建 `ParseService` 并接入注册中心（TDD）。
6. 切换 `routers/parse.py` 到 `ParseService`。
7. 运行全量回归测试。
8. 标记旧 `DownloadEngineAdapter` 为 deprecated（可选，视后续清理计划）。

**回滚策略**: 如果新模块出现问题，可立即将 `routers/parse.py` 切换回 `DownloadEngineAdapter`，旧模块保留不删除。
