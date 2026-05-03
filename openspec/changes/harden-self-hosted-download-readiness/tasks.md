# Tasks

## 1. OpenSpec And Docs

- [x] 1.1 新增个人自部署下载稳定性 OpenSpec 变更。
- [x] 1.2 更新执行计划、验收标准、运维合规文档，明确不替代公网 SaaS 门禁。

## 2. Worker And Task Stability

- [x] 2.1 增加 yt-dlp 保守重试、片段重试、超时和继续下载配置。
- [x] 2.2 下载进度回调中检测取消任务，避免取消后继续完成。
- [x] 2.3 增加下载、校验、上传、完成和失败事件。
- [x] 2.4 补充 Worker 单元测试覆盖取消、重试配置和失败归类。

## 3. Runtime Diagnostics

- [x] 3.1 `/ready` 增加队列和下载工作目录可写性检查。
- [x] 3.2 前端工作台增加轻量自部署状态提示。

## 4. Scripts And Validation

- [x] 4.1 新增过期对象清理脚本。
- [x] 4.2 新增个人自部署 smoke 聚合脚本。
- [x] 4.3 运行 OpenSpec、后端测试、脚本语法、前端 lint/build 和合规 smoke。
