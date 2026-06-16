## 1. 模块结构初始化

- [ ] 1.1 创建 `apps/api/app/sources/__init__.py`
- [ ] 1.2 创建 `apps/api/app/sources/adapters/__init__.py`
- [ ] 1.3 创建 `apps/api/tests/sources/__init__.py`
- [ ] 1.4 验证：`python -c "from app.sources import models"` 不报错

## 2. 领域模型（TDD）

- [ ] 2.1 创建 `apps/api/tests/sources/test_models.py`：为 `SourceRequest`、`SourceContext`、`SourceInfo`、`MediaVariant`、`SubtitleTrack`、`SourceCapability` 编写红灯测试
- [ ] 2.2 运行测试确认红灯：`pytest apps/api/tests/sources/test_models.py -v`（FAIL: module not found）
- [ ] 2.3 创建 `apps/api/app/sources/models.py`：实现 `SourceRequest`、`SourceContext`、`SourceInfo`、`MediaVariant`、`SubtitleTrack`、`SourceCapability`
- [ ] 2.4 运行测试确认绿灯：`pytest apps/api/tests/sources/test_models.py -v`（PASS）

## 3. 适配器协议（TDD）

- [ ] 3.1 创建 `apps/api/tests/sources/test_adapter_protocol.py`：为 `VideoSourceAdapter` ABC 编写红灯测试（supports/parse/map_error 约束）
- [ ] 3.2 运行测试确认红灯：`pytest apps/api/tests/sources/test_adapter_protocol.py -v`（FAIL: module not found）
- [ ] 3.3 创建 `apps/api/app/sources/adapter.py`：实现 `VideoSourceAdapter` ABC
- [ ] 3.4 运行测试确认绿灯：`pytest apps/api/tests/sources/test_adapter_protocol.py -v`（PASS）

## 4. 注册中心（TDD）

- [ ] 4.1 创建 `apps/api/tests/sources/test_registry.py`：为 `SourceAdapterRegistry` 编写红灯测试（register/get_adapter/fallback/default 初始化）
- [ ] 4.2 运行测试确认红灯：`pytest apps/api/tests/sources/test_registry.py -v`（FAIL: module not found）
- [ ] 4.3 创建 `apps/api/app/sources/registry.py`：实现 `SourceAdapterRegistry`
- [ ] 4.4 运行测试确认绿灯：`pytest apps/api/tests/sources/test_registry.py -v`（PASS）

## 5. 适配器实现迁移（TDD）

- [ ] 5.1 创建 `apps/api/tests/sources/test_adapters.py`：为 `YtDlpAdapter`、`BilibiliAdapter`、`DomesticShortVideoAdapter` 编写红灯测试（supports/parse/map_error 行为）
- [ ] 5.2 运行测试确认红灯：`pytest apps/api/tests/sources/test_adapters.py -v`（FAIL: module not found）
- [ ] 5.3 创建 `apps/api/app/sources/adapters/ytdlp.py`：实现 `YtDlpAdapter`
- [ ] 5.4 创建 `apps/api/app/sources/adapters/bilibili.py`：实现 `BilibiliAdapter`
- [ ] 5.5 创建 `apps/api/app/sources/adapters/domestic_short_video.py`：实现 `DomesticShortVideoAdapter`
- [ ] 5.6 创建 `apps/api/app/sources/adapters/__init__.py`：导出所有适配器
- [ ] 5.7 运行测试确认绿灯：`pytest apps/api/tests/sources/test_adapters.py -v`（PASS）

## 6. SourceInfo → ParseResponse 转换

- [ ] 6.1 在 `apps/api/app/sources/models.py` 中添加 `source_info_to_parse_response()` 函数
- [ ] 6.2 创建 `apps/api/tests/sources/test_conversion.py`：测试 SourceInfo → ParseResponse 转换（分辨率预设、watermark hint、stream type）
- [ ] 6.3 运行测试确认绿灯：`pytest apps/api/tests/sources/test_conversion.py -v`（PASS）

## 7. ParseService（TDD）

- [ ] 7.1 创建 `apps/api/tests/test_parse_service.py`：为 `ParseService` 编写红灯测试（delegation/error handling/response conversion）
- [ ] 7.2 运行测试确认红灯：`pytest apps/api/tests/test_parse_service.py -v`（FAIL: module not found）
- [ ] 7.3 创建 `apps/api/app/services/parse_service.py`：实现 `ParseService`
- [ ] 7.4 运行测试确认绿灯：`pytest apps/api/tests/test_parse_service.py -v`（PASS）

## 8. 路由集成

- [ ] 8.1 修改 `apps/api/app/routers/parse.py`：将 `DownloadEngineAdapter` 替换为 `ParseService`
- [ ] 8.2 运行回归测试：`pytest apps/api/tests/test_platform_profiles.py -v`（PASS）
- [ ] 8.3 运行回归测试：`pytest apps/api/tests/test_download_adapter.py -v`（PASS）
- [ ] 8.4 运行回归测试：`pytest apps/api/tests/test_platform_adapters.py -v`（PASS）
- [ ] 8.5 运行 API 合同测试：`pytest apps/api/tests/test_api_contract.py -v`（PASS）

## 9. 错误映射验证

- [ ] 9.1 创建 `apps/api/tests/sources/test_error_mapping.py`：测试各平台错误映射到统一 ErrorCode
- [ ] 9.2 运行测试确认绿灯：`pytest apps/api/tests/sources/test_error_mapping.py -v`（PASS）

## 10. 全量验证

- [ ] 10.1 运行源模块测试：`pytest apps/api/tests/sources -v`（ALL PASS）
- [ ] 10.2 运行全量测试：`npm test`（ALL PASS）
- [ ] 10.3 验证 router 无平台分支：人工审查 `routers/parse.py`
- [ ] 10.4 验证注册中心绕过检查：审查无直接 yt-dlp 调用绕过 registry
