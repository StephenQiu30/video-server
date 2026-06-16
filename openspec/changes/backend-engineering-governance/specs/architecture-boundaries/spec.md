# Architecture Boundaries

## Purpose

定义 video-server 后端各层的职责边界、依赖方向约束和禁止事项。

## ADDED Requirements

### Requirement: Router layer only handles protocol
Router 层 SHALL 只负责接收请求、调用 service 层和返回响应，不得包含业务逻辑或数据库操作。

#### Scenario: Router delegates to service
- **WHEN** API 接收请求
- **THEN** Router 只做参数解析、认证校验和响应序列化，业务逻辑由 service 层处理

#### Scenario: Router does not import ORM models
- **WHEN** 检查 `apps/api/app/routers/` 的 import 语句
- **THEN** 不得直接导入 `apps/api/app/models.py` 中的 ORM 模型

### Requirement: Schema layer only defines contracts
Schema 层 SHALL 只定义 Pydantic 请求/响应模型，不得包含业务逻辑或直接引用 ORM 模型。

#### Scenario: Schema uses Pydantic BaseModel
- **WHEN** 定义请求或响应模型
- **THEN** 使用 Pydantic `BaseModel`，不继承 SQLAlchemy 模型

### Requirement: Service layer only orchestrates
Service 层 SHALL 只做业务编排：协调 domain、repository 和 infrastructure，不得直接写 SQL 或直接调用外部 API。

#### Scenario: Service delegates DB operations to repository
- **WHEN** Service 需要读写数据库
- **THEN** 调用 repository 层函数，不直接操作 SQLAlchemy session

#### Scenario: Service delegates external calls to infrastructure
- **WHEN** Service 需要调用 Redis、MinIO 或队列
- **THEN** 调用 infrastructure 层函数，不直接使用外部客户端

### Requirement: Domain layer is pure business logic
Domain 层 SHALL 只包含纯业务规则：状态机、校验、计算。不得引用数据库、外部服务或框架组件。

#### Scenario: Domain function has no side effects
- **WHEN** 调用 domain 层函数
- **THEN** 函数不访问数据库、不调用外部服务、不修改全局状态

### Requirement: Repository layer encapsulates DB operations
Repository 层 SHALL 封装所有 SQLAlchemy 数据库操作，每个函数对应一个原子 CRUD 或查询操作。

#### Scenario: Repository receives session as parameter
- **WHEN** 调用 repository 函数
- **THEN** 函数接收 `db: Session` 作为参数，不自行创建会话

#### Scenario: Repository does not contain business logic
- **WHEN** 检查 repository 函数
- **THEN** 函数只做数据存取，不包含条件分支、状态转换或业务规则

### Requirement: Infrastructure layer encapsulates external services
Infrastructure 层 SHALL 封装 Redis、MinIO、队列等外部服务的调用。

#### Scenario: Infrastructure is a thin adapter
- **WHEN** 调用 infrastructure 函数
- **THEN** 函数只做协议转换和错误映射，不包含业务逻辑

### Requirement: Dependency direction is top-down
各层 SHALL 遵循从上到下的依赖方向：Router → Service → Domain / Repository / Infrastructure。下层不得依赖上层，同层不得循环依赖。

#### Scenario: No upward dependency
- **WHEN** 检查各层的 import 语句
- **THEN** repository 不导入 service，domain 不导入 service 或 router，infrastructure 不导入 service

#### Scenario: No circular dependency within same layer
- **WHEN** 检查同层模块的 import 语句
- **THEN** 不存在 A 导入 B 同时 B 导入 A 的情况

### Requirement: Module declares layer and dependencies
新增或重构模块 SHALL 在模块顶部注释或 docstring 中说明所属层级和允许的依赖方向。

#### Scenario: New module has layer annotation
- **WHEN** 开发者新增一个后端模块
- **THEN** 模块顶部包含 `# Layer: <layer_name>` 注释或等效 docstring
