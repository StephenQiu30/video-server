# 037 统一 AI 执行与 OpenRouter 接入计划

1. 失败优先测试覆盖独立 API 请求、模型能力拒绝、错误与结果限额。
2. 提取共享 API 分析策略，加入 Chat Completions 适配器和注册工厂。
3. 同步配置校验、SQL/ORM、目录 API、Web 编辑器和 OpenAPI 生成类型。
4. 执行后端 lint/type/tests 与前端 lint/tests/build，检查真实渲染。
5. 记录真实模型、跨平台、本地 Agent / 插件未完成边界；独立提交，不推送。

执行结果：上述实现与本地检查已完成；完整证据及尚未执行的真实模型、设备/插件验收见 Acceptance。未推送、未重启线上业务进程。
