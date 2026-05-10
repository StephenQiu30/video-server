# Tasks

## 1. OpenSpec

- [x] 1.1 新增本地 MVP 下载交互修补变更说明。
- [x] 1.2 补充交互反馈、历史展示和过期文件清理的规格增量。

## 2. Backend

- [x] 2.1 解析和创建任务前统一 URL trim、无协议补全和非法链接中文错误。
- [x] 2.2 `GET /api/tasks` 支持 `state`、`limit` 参数。
- [x] 2.3 列表和下载前轻量触发过期对象清理，保留任务历史。

## 3. Frontend

- [x] 3.1 解析、创建、下载、重试、取消动作补齐 loading、disabled 和错误提示。
- [x] 3.2 下载按钮稳定触发后端签名下载 URL。
- [x] 3.3 工作台只展示新建下载和少量当前/最近关键任务。
- [x] 3.4 任务历史页使用 ProTable 支持分页、状态筛选、详情和操作。

## 4. Docs And Validation

- [x] 4.1 更新 M1 执行计划和测试验收文档。
- [x] 4.2 更新 smoke 标题，避免测试任务占据工作台重点区域。
- [x] 4.3 运行 OpenSpec、后端测试、前端 lint/build 和 smoke 验收。
