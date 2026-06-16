## Context

video-server 当前目录结构：

```text
apps/api/app/
  routers/       — 协议层
  schemas.py     — Pydantic 契约
  services/      — 业务编排 + 数据库读写（职责混合）
  models.py      — SQLAlchemy ORM 模型
  core/          — 配置、错误处理、日志、安全
  db/            — 数据库会话和迁移
  middleware/    — 请求上下文
  utils/         — 工具函数

apps/worker/worker/
  jobs/          — 异步任务入口
  domain.py      — 业务规则
  download_runner.py — 下载执行
  ...

packages/shared/video_downloader_shared/
  states.py      — TaskState 枚举
```

设计文档 `docs/design/01-个人自部署万能视频下载器技术设计.md` §4.3 已定义目标分层（routers/schemas/services/repositories/worker-jobs/worker-adapters/shared），但当前实现缺少 `domain/`、`repositories/`、`infrastructure/` 目录，`services/` 层混合了业务编排和数据库操作。

### 现有问题

1. `services/tasks.py` 直接操作 SQLAlchemy session，违反 service 层只做业务编排的原则。
2. 错误码（`failure_code`）以字符串字面量分散在 `services/` 和 `worker/` 中，无统一定义。
3. 平台 ID 常量分散在 `services/platforms.py` 和 `worker/` 中。
4. 无架构边界测试，跨层依赖只能通过人工审阅发现。

## Goals / Non-Goals

**Goals:**

- 建立 domain、repository、infrastructure 分层目录骨架
- 将错误码、平台 ID 和跨模块 DTO 迁移到 `packages/shared/`
- 建立架构边界测试，自动验证依赖方向约束
- 建立复杂度控制检查脚本
- 渐进治理：不要求一次性迁移所有已有代码

**Non-Goals:**

- 不一次性重写 `services/` 层的所有数据库操作到 repository
- 不引入 CI 自动化架构扫描工具（import-linter 等）
- 不为 Worker 层创建独立的 repository（留待后续 PLAN）
- 不修改任何已有功能的行为

## Decisions

### 1. Domain 层为纯函数目录

**选择**：`apps/api/app/domain/` 存放纯业务规则函数，不引用数据库或外部服务。

**理由**：Domain 层是业务逻辑的核心，纯函数易于测试和复用。当前 `services/` 中的校验逻辑（如 URL 校验、并发检查）可逐步迁移到 domain。

### 2. Repository 层封装 SQLAlchemy 操作

**选择**：`apps/api/app/repositories/` 存放数据库读写函数，每个函数对应一个原子操作。

**理由**：将数据库操作从 service 层分离，使 service 只做业务编排。Repository 函数接收 session 作为参数，不自行创建会话。

### 3. Infrastructure 层封装外部服务

**选择**：`apps/api/app/infrastructure/` 存放 Redis、MinIO、队列等外部服务的适配函数。

**理由**：将外部服务调用从 service 层分离，便于 mock 测试和替换实现。

### 4. Shared 包使用模块文件而非子包

**选择**：新增 `codes.py`、`platforms.py`、`dto.py` 作为 `packages/shared/video_downloader_shared/` 下的模块文件。

**理由**：当前 `states.py` 已经是单文件模式，保持一致。跨模块常量规模不大，不需要子包拆分。

### 5. 架构边界测试通过 import 分析实现

**选择**：`test_architecture_boundaries.py` 通过解析 Python 源码的 import 语句验证依赖方向。

**理由**：不需要引入额外依赖（如 import-linter），测试本身即文档。通过 AST 解析 import 比正则匹配更可靠。

### 6. 复杂度检查脚本使用简单行数统计

**选择**：`scripts/check_complexity.sh` 检查 Python 文件行数，超过 200 行的文件报 warning。

**理由**：行数是最简单可靠的复杂度代理指标。圈复杂度检查需要额外工具（如 radon），留待后续评估。

## Risks / Trade-offs

- **风险**：渐进治理导致新旧代码风格并存 → **缓解**：架构边界测试确保新代码遵守约束，旧代码在被改动时逐步迁移
- **风险**：domain 层初始为空，可能被质疑过度设计 → **缓解**：从 `services/` 中提取第一个纯业务函数时才创建 domain 模块
- **风险**：shared 常量迁移可能引入循环依赖 → **缓解**：shared 包不依赖任何 app 代码，只被 app 代码单向依赖
