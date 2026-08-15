# 024 Docker 浏览器会话桥接验收

交付状态：已验收归档。

验收日期：2026-08-15

## 自动化验收

- 浏览器导出、TikTok extractor、权益策略、命令参数与 Settings 单元测试通过。
- 全量 `897` 项后端测试通过；数据库测试读取根 `.env` 并使用宿主机 PostgreSQL `5432`，未启动 Docker PostgreSQL。
- Ruff、格式检查、mypy 通过；开发/生产 Compose 配置可解析。
- Cookie Secret 未纳入 Git，Runner 启动日志不含 Cookie 值。

## 真实链路

| 平台 | 解析 | 下载 | Worker 共享卷 | 完整性 |
| --- | --- | --- | --- | --- |
| YouTube | `operator_managed / browser-v1`，22 个格式 | 144P MP4，3,850,174 bytes | 可见 | SHA-256、1 视频流、1 音频流通过 |
| TikTok | `operator_managed / browser-v1`，39 秒 | 1026P MP4，1,468,101 bytes | 可见 | SHA-256、1 视频流、1 音频流通过 |

TikTok 还通过已登录网页完成“链接解析 → 创建任务 → Worker 下载 → 完整性验证 → 获取视频文件”的产品端到端流程，任务一次执行成功。

测试期间产生的直接 Runner 临时制品已清理；产品端到端任务按系统保留策略留存。launchd labels 与原宿主机 Native Runner 运行目录均已撤销，备份位于系统废纸篓，可恢复。
