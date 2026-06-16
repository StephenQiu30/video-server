# Backend Layer Boundaries

## Purpose

定义 FastAPI 后端各层（router、service、repository、adapter、task、core、schema）的职责边界、依赖方向约束和单一事实来源要求，防止职责堆积和跨层反向依赖。

## ADDED Requirements

### Requirement: Router Layer SHALL NOT Directly Import External Download SDK

router 层 SHALL NOT 直接导入或调用 `yt_dlp`、`minio`、`redis` 等外部下载/存储 SDK。router 层 SHALL 通过 service 层或 adapter 层间接访问外部依赖。

#### Scenario: Router does not import yt-dlp directly
- **GIVEN** `apps/api/app/routers/` 目录下的任何 Python 文件
- **WHEN** 检查该文件的 import 语句
- **THEN** 文件 SHALL NOT 包含 `from yt_dlp` 或 `import yt_dlp`
- **AND** 文件 SHALL NOT 包含 `from minio` 或 `import minio`

#### Scenario: Router does not import database session directly
- **GIVEN** `apps/api/app/routers/` 目录下的任何 Python 文件
- **WHEN** 检查该文件的 import 语句
- **THEN** 文件 SHALL NOT 包含 `from app.db.session import SessionLocal`（除依赖注入的 `get_db` 外）
- **AND** 文件 SHALL 通过 `Depends(get_db)` 获取数据库会话

### Requirement: Service Layer SHALL Encapsulate Business Logic

service 层 SHALL 封装业务逻辑，包括并发检查、配额校验、任务状态流转、事件记录等。router 层 SHALL 通过调用 service 层函数完成业务操作，而非在 router 中直接操作数据库模型。

#### Scenario: Router delegates to service for business logic
- **GIVEN** router 层需要检查用户并发配额
- **WHEN** router 调用业务逻辑
- **THEN** router SHALL 调用 `services.tasks.assert_concurrency_allowed(db, user)` 而非直接查询数据库

### Requirement: Shared State and Error Codes SHALL Have Single Source of Truth

共享状态枚举（`TaskState`）、错误码（`ErrorCode`）、响应模型（`schemas.py`）SHALL 保持单一事实来源，不在多个模块中重复定义。

#### Scenario: TaskState defined once
- **GIVEN** `TaskState` 枚举在 `packages/shared/video_downloader_shared/states.py` 中定义
- **WHEN** 任何模块需要使用 `TaskState`
- **THEN** 模块 SHALL 从 `video_downloader_shared.states` 导入
- **AND** 模块 SHALL NOT 在本地重新定义 `TaskState`

#### Scenario: ErrorCode defined once
- **GIVEN** `ErrorCode` 枚举在 `app/core/errors.py` 中定义
- **WHEN** 任何模块需要使用 `ErrorCode`
- **THEN** 模块 SHALL 从 `app.core.errors` 导入
- **AND** 模块 SHALL NOT 在本地重新定义错误码

### Requirement: Dependency Direction SHALL Be Top-Down

依赖方向 SHALL 遵循：router → service → repository/adapter → model/core。下层 SHALL NOT 反向依赖上层。

#### Scenario: Service does not import from router
- **GIVEN** `apps/api/app/services/` 目录下的任何 Python 文件
- **WHEN** 检查该文件的 import 语句
- **THEN** 文件 SHALL NOT 包含 `from app.routers` 导入

#### Scenario: Core does not import from service or router
- **GIVEN** `apps/api/app/core/` 目录下的任何 Python 文件
- **WHEN** 检查该文件的 import 语句
- **THEN** 文件 SHALL NOT 包含 `from app.services` 或 `from app.routers` 导入

### Requirement: Repository Layer SHALL Abstract Database Operations

当需要复杂查询或跨模型操作时，SHALL 抽取到 repository 层或 service 层，避免在 router 中编写 SQLAlchemy 查询逻辑。

#### Scenario: Complex queries in service layer
- **GIVEN** router 需要执行包含 `select()`、`where()`、`order_by()` 的复杂查询
- **WHEN** 该查询涉及业务逻辑（如所有权校验、状态过滤）
- **THEN** 查询逻辑 SHALL 封装在 service 层函数中

### Requirement: Architecture Boundary Tests SHALL Exist

SHALL 维护架构边界测试，约束 router 层不直接依赖外部 SDK，并验证依赖方向正确性。

#### Scenario: Architecture boundary test file exists
- **GIVEN** `apps/api/tests/test_architecture_boundaries.py`
- **WHEN** 运行 `pytest apps/api/tests/test_architecture_boundaries.py -v`
- **THEN** 测试 SHALL 验证 router 层的 import 边界
- **AND** 测试 SHALL 验证依赖方向约束

### Requirement: Large Files SHALL Be Split or Justified

超过 200 行的文件 SHALL 按职责拆分，或在 PR 中给出保留理由。

#### Scenario: File exceeds 200 lines
- **GIVEN** 一个 Python 文件超过 200 行
- **WHEN** 该文件被本次变更修改
- **THEN** 文件 SHALL 被拆分为更小的模块
- **OR** PR 中 SHALL 包含保留该文件的理由说明
