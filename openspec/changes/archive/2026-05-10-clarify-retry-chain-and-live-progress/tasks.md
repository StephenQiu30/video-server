# Tasks

## 1. OpenSpec And Docs

- [x] 1.1 新增重试链路和实时任务流 OpenSpec 变更。
- [x] 1.2 更新执行计划和测试场景，明确重试链只按显式关系折叠。

## 2. Backend Retry Chain

- [x] 2.1 为任务模型、Schema 和数据库升级脚本增加 `retry_of_task_id`、`attempt_no` 和最新尝试标记。
- [x] 2.2 修正重试规则：只允许 failed、canceled、过期或对象缺失的 succeeded 重试，禁止 queued/running 和已被重试的旧任务再次重试。
- [x] 2.3 增加后端测试覆盖重试链、重复重试拦截和历史回填。

## 3. Live Progress

- [x] 3.1 新增 `GET /api/tasks/stream` SSE 任务流。
- [x] 3.2 前端接入 `EventSource`，并保留失败后的手动刷新或轻量轮询降级。

## 4. Frontend Task Display

- [x] 4.1 工作台只展示每条重试链最新任务。
- [x] 4.2 任务历史和详情展示尝试次数、已重试和最新任务状态。

## 5. Validation

- [x] 5.1 运行 OpenSpec、后端测试、脚本语法、前端 lint 和 build。
