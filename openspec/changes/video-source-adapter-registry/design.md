# Design: 视频源适配器与注册中心

## Goals

- 将现有适配器实现规范化为可扩展的适配器体系
- 确保新增平台不修改 parse router 或任务创建主流程
- 统一所有适配器的失败语义映射

## Non-goals

- 不引入动态插件加载或远程 adapter 机制
- 不修改 `/api/parse` 路由签名或 `ParseResponse` 结构
- 不实现 Worker 下载执行或 MinIO 归档逻辑

## Contracts

### PlatformAdapter 接口

```python
class PlatformAdapter:
    name: str

    def supports(self, parsed_host: ParsedHost) -> bool:
        """判断是否支持该 URL"""

    def parse(self, url: str) -> ParseResponse:
        """解析 URL 并返回统一响应"""

    def map_parse_error(self, exc: Exception) -> AppError:
        """将异常映射为统一错误码"""
```

### AdapterRegistry 注册

```python
class AdapterRegistry:
    def __init__(self, adapters: list[PlatformAdapter] | None = None):
        # 默认顺序：专用适配器 → YtDlpAdapter

    def get_adapter(self, url: str) -> PlatformAdapter:
        # 按顺序匹配，第一个 supports() 返回 True 的适配器被选中
        # 若无匹配，返回最后一个适配器（YtDlpAdapter）
```

### DownloadEngineAdapter 门面

```python
class DownloadEngineAdapter:
    def __init__(self, registry: AdapterRegistry | None = None):
        self._registry = registry or AdapterRegistry()

    def parse(self, url: str) -> ParseResponse:
        adapter = self._registry.get_adapter(url)
        try:
            return adapter.parse(url)
        except AppError:
            raise
        except Exception as exc:
            raise adapter.map_parse_error(exc) from exc
```

## State Flow

1. 用户提交 URL → `DownloadEngineAdapter.parse(url)`
2. `AdapterRegistry.get_adapter(url)` 匹配适配器
3. 适配器调用 yt-dlp 解析
4. 成功 → 返回 `ParseResponse`
5. 失败 → `map_parse_error()` 映射为统一 `AppError`

## Failure Paths

| 异常特征 | 错误码 | HTTP | 消息 |
| --- | --- | --- | --- |
| login/sign-in/members-only/private/premium/paid/drm/copyright/geo | `platform_restricted` | 403 | 内容存在访问限制 |
| too many requests/429/rate limit/captcha | `platform_rate_limited` | 429 | 平台访问频率受限 |
| unsupported url/no suitable extractor | `unsupported_platform` | 422 | 该链接暂不支持解析 |
| timed out/timeout/connection reset | `platform_unavailable` | 503 | 平台暂时不可访问 |
| 其他 | `parse_failed` | 422 | 公开视频解析失败 |

## Rollback Impact

- 本变更为纯文档和规范层新增，不修改现有代码行为
- 回滚方式：删除新增的文档和 OpenSpec 文件
