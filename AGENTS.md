# AGENTS.md

更新时间：2026-05-03

## 1. 项目协作原则

本项目是“合规、安全、可自部署的万能视频下载与内容整理工具”。所有 Agent 和开发者必须先遵守产品边界、合规边界和技术确认流程，再进入实现。

## 2. 当前阶段规则

当前已完成调研、边界确认和关键技术选型确认。项目可以进入 M1 MVP 骨架阶段，但必须遵守已确认技术栈、合规边界和 OpenSpec 变更管理流程。

已确认的关键选型包括：

- 前端：React + Umi + TypeScript + Ant Design Pro。
- 后端：FastAPI + Python 3.12。
- 下载内核：yt-dlp + FFmpeg / ffprobe。
- 队列和数据库：RQ + Redis + PostgreSQL。
- 文件存储：MinIO / S3 兼容对象存储，私有 bucket + 后端短期签名代理下载 URL。
- UI 组件库：Ant Design Pro。
- AI 摘要：二期再做。
- 平台专用解析：首版不做，只预留插件口。
- 鉴权：M1 本地单用户模式，不要求注册、登录或 JWT；JWT 用户系统归入上线级 SaaS。
- 本机 B 站下载：M1 允许本机 Worker 按 `YTDLP_COOKIES_FROM_BROWSER=chrome` 读取当前机器 Chrome 登录态，用于下载当前用户自己可访问且有权保存的内容；不得保存、上传、入库或记录 Cookie。
- OpenSpec：M1 使用 `bootstrap-mvp-foundation` 和收尾小变更管理；下载闭环稳定化使用 `stabilize-local-mvp-download-flow`，B 站本机真实链路使用 `support-local-bilibili-download-flow`。

## 2.1 上线级 SaaS 内测阶段规则

上线级 SaaS 补齐必须单独通过 OpenSpec 变更 `production-saas-readiness` 管理，不得混入 M1 本地 MVP 变更。

已确认的第一版上线基线：

- 小范围内测 SaaS。
- 免费配额，不接入支付。
- 单机 Docker Compose + Nginx/TLS。
- 先补齐注册控制、免费配额、限流、管理员兜底、部署、备份、日志、监控和合规验收。

上线级补齐阶段禁止未经确认引入：

- 支付、会员、订阅、发票。
- K8s、服务网格、多地域高可用。
- 复杂团队权限或组织体系。
- 用户平台 Cookie 托管。
- 平台专用解析。
- AI 摘要、问答、思维导图。

所有生产化能力必须有可执行验收命令或可观察证据；无法验证的能力不得标记为完成。

## 3. 合规边界

允许：

- 下载用户拥有版权、已获授权、公共领域、开放授权或平台明确允许保存的内容。
- 解析公开可访问的视频信息。
- 提供字幕、摘要、音频提取、格式转换和素材整理。
- 在自部署环境中进行受控下载任务。

禁止：

- 规避 DRM、付费墙、会员限制或访问控制。
- 提供盗版传播、批量滥采或账号共享能力。
- 未经确认托管用户平台 Cookie；M1 本机 Worker 读取 Chrome 登录态属于本机单用户例外，不等同于 Cookie 托管。
- 在日志中保存完整私密链接、Cookie、Authorization、签名参数。
- 宣传“可下载任意受保护内容”。

## 4. 文档规范

- `docs/README.md` 是文档入口。
- 文档按“编号 + 中文功能文件夹 + 编号中文文档”管理。
- `docs/00-文档总览/00-文档索引.md` 是完整文档导航。
- 市场调研放在 `docs/01-市场调研/`。
- 产品需求放在 `docs/02-产品需求/`。
- 架构设计和技术选型放在 `docs/03-架构设计/`。
- 执行计划放在 `docs/04-执行计划/`。
- 测试验收放在 `docs/05-测试验收/`。
- 运维合规放在 `docs/06-运维合规/`。
- 归档资料放在 `docs/07-归档/`。
- 角色定义放在 `.codex/agents/`。
- 可复用工作流放在 `.codex/skills/`。
- 新增关键技术决策时，必须补充 ADR 或在 `docs/03-架构设计/03-架构决策记录.md` 中留痕。
- 文档优先使用中文。
- docs 文件夹和文件命名使用两位编号 + 中文功能名，避免随意命名。

## 5. 工程实现规范

在进入实现阶段后：

- 保持前后端、Worker、存储、AI 能力边界清晰。
- 下载内核必须封装在适配层中，不允许散落在业务代码里。
- 所有下载任务必须有状态机：queued、running、succeeded、failed、canceled。
- 所有任务必须有超时、最大文件大小、并发限制和过期清理策略。
- 文件名必须清洗，禁止路径穿越。
- API 错误必须能被前端展示为用户可理解的原因。
- 默认使用 Docker 或项目本地环境验证，避免污染宿主系统。

## 6. 测试与验收规范

- 每个下载能力必须有公开授权或可公开访问的样例。
- 验收必须覆盖成功样例和失败样例。
- 不得用受保护、付费、会员、盗版或隐私链接作为默认测试样例。
- 下载相关测试需要控制文件大小，避免无意义消耗带宽和磁盘。
- 前端实现必须验证桌面和移动端基本布局。

## 6.1 后端 MVP 逐步验收规范

后端服务必须按“最小可用链路”一步一步验收，不允许为了追求完整平台化而提前引入复杂架构。

参考鱼皮 `free-video-downloader` 的实现方式时，只吸收它的 MVP 思路：FastAPI 暴露少量清晰接口，下载能力集中封装在 `yt-dlp` 适配层，先跑通“解析 -> 下载 -> 返回文件/链接”的核心链路。不要照搬 AI 总结、支付、会员、SEO、抖音专用解析等超出当前 M1 范围的能力。

执行顺序固定为：

1. 检查 `.env` 中 PostgreSQL、Redis、MinIO / S3、下载限制配置是否与本地服务一致；JWT 只作为上线级 SaaS 配置保留，不作为 M1 登录门槛；如需要 B 站登录态下载，确认 `YTDLP_COOKIES_FROM_BROWSER=chrome` 只由本机 Worker 使用。
2. 检查 PostgreSQL、Redis、MinIO / S3 端口和认证是否可用。
3. 启动 FastAPI，只验收 `/health`、`/ready`、解析和任务接口；M1 默认不验收注册、登录、当前用户接口。
4. 启动 RQ Worker，只验收任务入队和状态流转。
5. 验收解析接口，只使用公开视频样例，不引入平台专用解析。
6. 验收一个小文件下载闭环：创建任务、Worker 下载、本地 FFmpeg 合并、ffprobe 校验、上传私有 bucket、生成后端短期签名代理下载 URL，并实际下载文件。
7. 验收失败路径：队列不可用、任务未完成获取下载链接、伪造或过期下载签名、过期文件、URL 脱敏、Chrome 登录态不可读；未登录、重复邮箱和密码错误迁移到上线级 SaaS 验收。
8. 验收 B 站本机真实链路：解析 B 站链接、创建推荐格式任务、本机 Worker 下载、上传私有 bucket、通过后端签名代理 URL 保存非空文件。

MVP 阶段禁止：

- 未经确认改用 Celery、RabbitMQ 或其他队列架构。
- 未经确认新增平台专用解析、Cookie 托管、DRM 绕过、付费墙绕过。
- 将本机 Worker 浏览器登录态读取扩展成前端 Cookie 上传、API Cookie 入参、数据库 Cookie 保存或公网 SaaS Cookie 托管。
- 为了“以后可能用到”提前引入微服务、消息总线、复杂权限、多租户或支付能力。
- 在后端基本链路未验收前继续堆叠前端功能。

FFmpeg / ffprobe 使用边界：

- M1 本地验收阶段只验证本机已安装的 FFmpeg / ffprobe 是否可用，不把 Docker 上线环境作为当前阻塞项。
- FFmpeg / ffprobe 是 API / Worker 的运行时依赖，Worker 下载和校验时必须能直接调用。
- 不在 `/Users/stephenqiu/Desktop/Docker` 中新增独立 FFmpeg 服务；该集中 Docker 仓库只管理 PostgreSQL、Redis、MinIO 等长期运行的基础设施。
- Docker 镜像是否内置 FFmpeg / ffprobe 留到上线部署阶段再验收，MVP 阶段不为此扩大实现范围。

MVP 阶段优先保留的接口形态：

- `POST /api/parse`：输入 URL，返回标题、封面、时长、格式列表。
- `POST /api/tasks`：创建下载任务；如果需要同步直返能力，必须先说明与任务队列的关系。
- `GET /api/tasks/{task_id}`：查询任务状态。
- `POST /api/tasks/{task_id}/cancel`：取消任务。
- `GET /api/tasks/{task_id}/download-link`：任务完成后返回短期下载链接。
- `GET /api/tasks/{task_id}/download`：通过后端短期签名代理流式下载文件。
- `GET /api/tasks/{task_id}/events`：查询任务事件历史。
- `POST /api/tasks/{task_id}/retry`：失败、取消或过期任务创建新的重试任务。

如果参考项目中存在更简单的实现方式，优先评估是否能减少当前 M1 的复杂度；但不得绕过已确认的合规边界和用户已确认的关键选型。

如果某一步未通过，只修复当前步骤的最小问题，并记录验证结果；不要跨步骤扩展范围。

## 7. 安全规范

- 日志脱敏是默认要求。
- URL 参数中的 token、signature、auth、cookie、key 等字段必须脱敏。
- 后台 Worker 只能写入受控下载目录。
- 公网部署必须启用鉴权、限流和任务配额。
- 下载完成文件必须有保留期限。

## 8. Agent 行为规范

- 不要偏离已确认关键选型；如需调整，先更新 ADR 和 OpenSpec。
- 不要为了“万能”而扩大范围。
- 不要把平台专用解析作为默认能力。
- 遇到合规不确定内容，先记录风险并请求确认。
- 每次实现后更新对应文档。
- 交付时说明验证命令、验证结果和未验证风险。

## 9. `.codex` 协作结构

- `.codex/agents/pm.toml`：拆需求、控范围、定义 MVP 和验收标准。
- `.codex/agents/architect.toml`：维护架构、技术候选、ADR 和模块边界。
- `.codex/agents/explorer.toml`：只读探索上下文、代码、文档和资料。
- `.codex/agents/builder.toml`：在选型确认后做最小实现。
- `.codex/agents/tester.toml`：测试、回归、验收和失败样例。
- `.codex/agents/reporter.toml`：汇总交付结果、验证证据和风险。
- `.codex/agents/compliance.toml`：审查版权、DRM、付费墙、Cookie 和隐私风险。
- `.codex/agents/devops.toml`：维护 Docker、部署、存储、清理、限流和监控。

标准协作流程为 Explorer -> PM -> Architect -> Compliance -> Builder -> Tester -> Reporter。复杂任务必须按此流程拆分，小任务可以合并角色，但不能跳过合规和验收边界。
