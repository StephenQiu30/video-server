# 037 统一 AI 执行与 OpenRouter 接入验收

日期：2026-09-17。状态：代码与确定性验证完成，真实付费模型待验收。

## 实现

- 原 DeepSeek 分析、抽帧、资源约束提取为 ai_api，共享视频、剧本分析、汇总、术语表和改写流程。
- 注册工厂统一选择 Codex、Claude、DeepSeek、OpenRouter、OpenAI 兼容线路；API 线路无需 Codex/Claude 可执行程序。
- OpenRouter 公开模型目录、五分钟缓存、图像/文本/结构化输出准入，严格 schema 与 require_parameters，关闭供应商 fallback。
- 非流式 Chat Completions 有界响应、超时、取消、错误脱敏、拒绝重定向、不自动重试。保留业务结果校验。
- Web 配置、目录搜索/选择、API-only 认证约束、OpenAPI 生成客户端；切换服务地址/引擎必须显式提供凭据。
- 编辑弹窗关闭恢复触发器焦点。

## 验证证据

- Red：新增协议测试首先因缺少 ai_api 模块失败；实现后通过。
- 后端 ruff check / format、mypy 通过；全量 pytest 1825 passed、2 skipped。跳过为未配置隔离 MinIO、当前 macOS 不支持 Linux O_PATH。
- 另增真实 PostgreSQL 隔离 schema 测试 1 passed，验证新引擎合法插入、拒绝 host_login 和 OpenRouter 非官方地址。测试 schema 自动清理。
- 前端 lint/typecheck、format 和 production build 通过；最终全量测试 300 passed（64 个文件），焦点修复相关回归通过。happy-dom 测试运行有 AsyncTaskManager 清理噪声，不冒充浏览器运行错误。
- 本机既有数据库仅幂等更新三项 Provider CHECK 约束，3 项确认存在；未更新配置、凭据或活动线路。
- 真实公开 OpenRouter 目录读取成功：444 个模型、360 个文本结构化候选、239 个视觉结构化候选。这是查询当时的能力声明，不代表模型调用成功。
- 候选生产构建在独立 127.0.0.1:8128 验证；上游设置不可用端口，浏览器仅注入合成管理员/目录，不写生产 API。1280×900、390×844 明暗主题无页面横向溢出，模型选择写回输入，Escape 关闭后焦点返回“新增 AI 服务”。axe 页面 0 violations / 0 incomplete；弹窗 0 violations、1 项 aria-hidden-focus 人工复核项，键盘实际焦点在弹窗内且关闭恢复触发器。截图 /tmp/framefetch-ai-{desktop,mobile}{,-dark}.png，未提交临时图片。

## 未验证边界

- 未使用真实 API Key 进行 OpenRouter / 通用服务的付费视频分析；能力目录与 MockTransport 不能替代此验收。
- 未重新运行 Codex/Claude 真实模型、跨平台常驻、整套 Compose 或发布部署；已覆盖其确定性回归。
- 用户设备 Agent 发行/配对、Codex App 插件和原生 Anthropic/Responses 直连未在本切片实现。037 为这些入口提供共享分析策略，并不宣称设备调度已交付。
