# 项目工程规范

本文规定 `video-server` 的目标工程标准，自 2026-09-18 起生效。标准依据框架官方约定和本项目已明确的需求制定，禁止依据现有目录反推规范。新增与重构代码必须遵守；现有代码仅作为迁移和验收对象。Flutter App 为独立项目，单独维护规范。

本文负责技术、目录和依赖规则；AGENTS.md 负责协作与交付；README.md 负责运行方式；design.md 负责界面。发生架构冲突时，以本文和用户最新要求为准。

## 1. 技术标准

| 范围 | 规定 |
| --- | --- |
| 后端 | Python、FastAPI、Pydantic；使用 uv 和 uv.lock 管理依赖 |
| 持久化 | PostgreSQL、SQLAlchemy 异步 Session；数据模型与 HTTP 模型分离 |
| 前端 | 官方 create-next-app：Next.js App Router、React、TypeScript strict、Tailwind CSS |
| 组件 | 官方 shadcn CLI 与 Radix 组件；不自行实现平行基础组件库 |
| 前端依赖 | pnpm；packageManager 固定版本，唯一 pnpm-lock.yaml |
| 接口契约 | FastAPI 注解自动生成 OpenAPI，Swagger UI 展示同一份契约 |
| 接口调用 | @umijs/openapi 生成 src/api，统一使用 Axios src/lib/request.ts |
| 长任务 | 独立 Worker；HTTP 接口负责提交、查询、取消，不执行长时间媒体或 AI 工作 |
| 检查 | 后端 Ruff、mypy、pytest；前端 Biome、TypeScript、Vitest、Next.js build |

具体版本通过依赖清单与锁文件固定；禁止在本文维护另一份版本快照。新依赖必须承担明确职责，不因脚手架默认包含就保留。

## 2. FastAPI 工程结构

### 2.1 官方基线

采用 FastAPI 官方 **Bigger Applications — Multiple Files** 的多文件应用方式：Python package、`main.py`、`dependencies.py`、`routers/`，通过 `APIRouter` 和 `include_router()` 组织接口，通过 `Depends` 提供依赖。FastAPI 保留组织代码的灵活性，没有规定唯一的业务架构。

### 2.2 目录规范

```text
backend/
├── pyproject.toml
├── uv.lock
├── app/
│   ├── __init__.py
│   ├── main.py                 FastAPI 应用入口和路由注册
│   ├── dependencies.py         共享的 Depends 依赖函数
│   └── routers/
│       ├── __init__.py
│       └── <业务>.py           按业务组织的 APIRouter
└── tests/                      与应用模块对应的测试
```

这是本项目选定的官方多文件应用基线。官方示例中的 users、items、internal/admin 是演示模块，不要求创建这些业务或空目录。Python 包使用 `__init__.py`，模块采用明确的包导入，避免同名模块冲突。

本项目需要的额外模块按以下职责增加；这些是项目约定，不能标成 FastAPI 强制目录：

| 模块 | 职责与拆分条件 |
| --- | --- |
| schemas.py | Pydantic 请求和响应模型；业务数量增长时拆成 schemas/ 包 |
| models.py | SQLAlchemy 数据库模型；需要时按业务拆成 models/ 包 |
| database.py | Engine、Session 配置及资源管理 |
| config.py | 类型化的应用配置 |
| 具体业务模块 | 被路由或 Worker 复用的实际业务操作，以业务命名 |
| workers/ | 媒体、下载、AI 等独立进程入口，按实际任务创建 |

同一职责只保留一个入口；模块拆成包时更新全部导入，不同时保留同名文件与包。简单操作可以直接写在路径操作函数中；复杂或复用的业务逻辑再提取。不得为每个接口创建固定的一整套类、接口与转发文件。

### 2.3 FastAPI 实现规则

- `main.py` 创建应用并用 `include_router()` 注册业务路由；路由模块导出 `APIRouter`，不能反向导入主应用。
- 路径操作以类型注解声明参数，使用 Pydantic 校验请求与过滤响应；显式声明稳定的 operation_id、tag、状态码及额外响应。
- 共享的认证、当前用户、会话等依赖由 `dependencies.py` 提供，使用 `Depends` 注入；仅被单个路由使用的依赖可就近定义。
- 数据库会话按请求或任务隔离，使用明确的释放机制；事务所有权必须明确并验证回滚，不能因目录调整改变提交行为。
- 连接池等运行资源由 lifespan 管理；导入应用与生成 OpenAPI 不应连接外部服务或启动 Worker。
- 异步路径不执行阻塞 IO 或 CPU 密集工作；长任务交给独立 Worker，复用业务操作时保持一致的权限检查。
- Python 模块与函数使用 snake_case，类使用 PascalCase；输入和输出模型按语义命名，避免以 Any 或自由 dict 代替稳定契约。
- 使用 FastAPI 的依赖覆盖与测试客户端验证认证、输入校验、响应过滤和异常；测试不需要为每个函数创建一层抽象。

## 3. Swagger 与生成 API（必须遵守）

唯一维护链路：**路由装饰器 + Pydantic 模型 → FastAPI /openapi.json → @umijs/openapi → frontend/src/api/**。

- `/docs` 展示 Swagger UI；不手写 JSON/YAML 契约，不手动维护平行接口文档。
- 每个公开操作有稳定且唯一的 operation_id 和业务 tag。字段、错误、分页、可空与二进制响应均在后端注解中声明。
- 接口类型和请求函数全部自动生成；不得编辑 src/api，禁止复制 DTO 或创建别名聚合层。
- openapi2ts.config.ts 是唯一生成配置；执行 pnpm openapi，不另写生成包装脚本。
- 生成请求统一导入 src/lib/request.ts 的 Axios 封装；认证恢复、超时、取消和错误归一化由请求基础设施处理。
- CI 从后端源码自动导出临时 schema，重新生成并检查 Git 差异。禁止只用旧服务的 Swagger 验证新代码。
- 后端业务实现、外部对象存储传输和 WebSocket 协议不由 REST 客户端生成器代替。

## 4. 前端目录与文件规则

依据 Next.js 官方文件约定组织路由，采用业务就近放置的源码组织方式。

```text
frontend/
├── package.json / pnpm-lock.yaml
├── components.json             shadcn CLI 配置
├── openapi2ts.config.ts         唯一接口生成配置
├── src/
│   ├── app/                    page、layout、loading、error、元数据等框架入口
│   ├── api/                    自动生成的请求函数与类型
│   ├── components/
│   │   ├── ui/                 官方 shadcn 基础组件
│   │   └── <业务>/             业务组件、专用 Hooks 和界面逻辑
│   ├── hooks/                  跨业务共享的 React Hooks
│   └── lib/                    Axios、浏览器能力及真正共享的非 React 代码
├── public/                     产品实际使用的静态资源
└── tests/                      测试、fixtures 和 helpers
```

- 单页面状态优先在组件内维护；需要独立职责或复用时再拆 Hook，业务专用 Hook 就近放置。
- 跨业务且使用 React 生命周期的能力进入 hooks；纯函数不能因名称含 use 就成为 Hook。
- lib 按职责组织，可为复杂共享能力建立子目录；不能把单业务文案、接口别名或 UI 塞入 lib。
- 不设置平行 services/utils/types 聚合层，不以改变目录名字代替删除无用途抽象。
- 普通文件 `kebab-case.ts/tsx`，Hook 文件 `use-*.ts`、函数 `useXxx`；Next.js 特殊文件和生成 API 保持工具约定。
- 接口直接使用 `API.*`；前端独有类型在所属业务附近定义。禁止为类型改名建立文件。
- UI 优先 Server Component，交互需要时再使用 Client Component；Server-only 能力不能经共享模块导入浏览器。
- 基础组件使用官方源码与 API；按需安装，不预存未使用组件，不维护假用户、模拟业务入口或演示资产。

## 5. 清理与变更规则

- 创建文件前必须说明独立职责和实际调用方。禁止空目录、纯转发文件、重复类型、备用实现和无用途 barrel。
- 删除前核对源码、动态加载、框架入口、构建配置和测试；无普通 import 不等于无用，测试引用也不等于生产必需。
- 删除时同步清理 COPY、命令、依赖、测试夹具与当前文档入口；不通过删除业务回归测试掩盖功能损坏。
- 前后端分别管理依赖，禁止把独立 App 的规范写入本项目。Secret、本机配置、Cookie、制品、缓存和日志不进入 Git。
- 不因目录迁移改变公开 URL、权限、数据库语义和消息格式。一次迁移必须覆盖引用、导入入口、测试与部署入口，不保留旧路径兼容层。

## 6. 验收与迁移状态

新规范不能用文档提交代替代码验收：

- 后端：Ruff、mypy、pytest；覆盖路由注册、依赖注入、事务成功/回滚、响应字段过滤和 OpenAPI。
- 前端：format、lint、TypeScript、Vitest、production build；接口变化必须重生成。
- 镜像或运行入口变化必须验证构建；界面行为变化补浏览器验证；平台下载需真实任务验证。
- 推送 main 前核对暂存内容和远端状态；推送后检查同一提交的 CI，并报告失败或尚未完成的检查。

本次修订交付的是**规范**。后端现有代码尚未按本节目标结构完成整体迁移，不能宣称已完成 FastAPI 目录调整。后续迁移按一个完整业务用例逐步实施，并以测试和运行证据确认；不将现有目录自动视为符合规范。

## 7. 官方依据

- [FastAPI 多文件应用与 APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI 依赖注入](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI 请求/响应模型](https://fastapi.tiangolo.com/tutorial/response-model/)
- [FastAPI 数据库会话示例](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [Next.js 工程结构](https://nextjs.org/docs/app/getting-started/project-structure)
- [shadcn Next.js 安装](https://ui.shadcn.com/docs/installation/next)

官方基线与项目扩展分别标明；目录规范不以现有实现为依据。
