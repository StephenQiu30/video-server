## Context

视频下载后端采用 FastAPI 构建，当前目录结构为：

```
apps/api/app/
├── core/          # 配置、错误码、日志、安全、响应封装
├── db/            # 数据库会话
├── middleware/    # 请求上下文中间件
├── models.py      # SQLAlchemy 模型
├── routers/       # API 路由层
├── schemas.py     # Pydantic 响应/请求模型
├── services/      # 业务逻辑层
├── utils/         # 工具函数
└── main.py        # FastAPI 应用入口
```

当前问题：
1. router 层（`routers/tasks.py`）已正确通过 service 层调用业务逻辑，但缺少显式的架构边界约束。
2. `routers/parse.py` 直接调用 `DownloadEngineAdapter`（属于 adapter 层），虽然合理但未在规范中明确。
3. 缺少 `repositories/`、`sources/`、`tasks/` 目录的定义和规范。
4. 缺少架构边界测试来防止未来引入跨层依赖。

### 现有依赖关系

```
routers/tasks.py
  ├── services/tasks.py (业务逻辑)
  ├── services/queue.py (入队)
  ├── services/rate_limit.py (限流)
  ├── services/storage.py (对象存储)
  ├── services/platforms.py (平台校验)
  ├── utils/url.py (URL 规范化)
  └── core/config.py (配置)

services/tasks.py
  ├── models.py (数据库模型)
  ├── core/errors.py (错误码)
  ├── core/config.py (配置)
  └── video_downloader_shared.states (共享状态)
```

## Goals / Non-Goals

**Goals:**

- 固化后端分层架构边界和依赖方向
- 建立架构边界测试防止回归
- 创建 PRD08 和 PLAN13 文档补齐治理链路
- 更新验证脚本检查文档完整性

**Non-Goals:**

- 不做大规模代码重构或目录迁移
- 不引入新的 `repositories/` 或 `sources/` 目录（当前代码规模不需要）
- 不改动前端工程规范
- 不改动 Worker 内部实现

## Decisions

### 1. 保持现有目录结构，通过规范约束

**选择**：不引入新的 `repositories/`、`sources/`、`tasks/` 目录，而是通过文档和测试约束现有结构的职责边界。

**理由**：当前代码规模（~20 个文件）不需要额外的分层抽象。引入新目录会增加复杂度，不符合最小实现原则。

### 2. Router 层通过 service 层访问业务逻辑

**选择**：router 层 SHALL 通过 `services/` 模块调用业务逻辑，不直接操作数据库模型或外部 SDK。

**理由**：当前 `routers/tasks.py` 已经遵循此模式，只需固化为规范。

### 3. 允许 router 层直接使用 adapter 层

**选择**：`routers/parse.py` 可以直接调用 `DownloadEngineAdapter`，因为 adapter 本身就是 router 的直接依赖。

**理由**：adapter 层是 router 的直接下游，调用 adapter 不违反依赖方向。

### 4. 通过 AST 分析实现架构边界测试

**选择**：使用 Python AST 模块解析 router 文件的 import 语句，验证不包含禁止的导入。

**理由**：AST 分析是静态检查，不依赖运行时环境，可以在 CI 中稳定运行。

## Risks / Trade-offs

- **风险**：AST 分析可能误报（如注释中的 import 语句）→ **缓解**：只检查实际的 import 节点，忽略注释
- **风险**：未来引入新目录时需要更新规范 → **缓解**：在 PRD08 中明确目录扩展流程
