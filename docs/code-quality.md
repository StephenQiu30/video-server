# 代码质量问题与修复登记

- 更新：2026-09-12；用户已批准开始全面实施，按独立切片修复与验收，未通过的可行性门禁不视为自动通过。
- 服务端/Web 基线：`8ef415ce638131747988b033d5eb12916d20890e`；App 基线：`7439f49a6a4da1d6f1212ca43a058c4a82f55dd9`。
- 范围：当前平台访问设计、下载/上传及状态恢复链路，延伸到相邻分析校验、并发测试和 App 下载操作。使用文本重复候选扫描、实现/调用方/测试人工核对；不是全仓逐行审计，不证明未列区域不存在问题。
- 初次审查只改治理和设计文档；本轮已进入实施。App 原有 4 个已修改 Dart 文件及 1 个未跟踪测试原样保留，未搭车提交；发现项不以这些原有未提交修改为证据。
- 与 [018 业务评审](research/018-业务逻辑评审与ToC最小上线能力.md)分工：018 保留业务/上线事实；本文维护代码质量缺陷及去重裁决。已修复的 App 会话/分析竞态不重复记为未修复。

## 1. 登记和关闭规则

代码整洁以正确性、可维护性和职责清晰为目标，不以行数、文件数或“所有相似代码都合并”为目标。

每条记录必须包含：稳定 ID、分类、优先级、证据及基线、具体影响、最小修复、保留边界、验收、当前状态。源码事实、推断风险、实测复现分别标记，不能把搜索命中直接算缺陷。

- 分类：行为缺陷、验证缺陷、重复规则、过度设计风险；架构复杂但有职责依据的可裁决保留。
- 优先级：P0 数据/安全紧急事故；P1 严重阻断核心流程；P2 有明确影响的功能或测试问题；P3 无当前行为错误证据的维护性问题。优先级不替代证据强度。
- 流程：待核实 → 已确认待修复 → 方案就绪 → 已修复待验收 → 已关闭。设计候选可保留条件限制；不采纳必须写原因，不静默删除记录。
- 关闭需填写修复 commit、稳定的回归测试和执行结果；涉及状态、契约、数据库、部署或真机时，补对应证据。测试通过但没有覆盖发现项，不能关闭。
- 后续修改触及登记项时，先核对当前事实与影响范围，在批准的切片中完成 Red→Green→Refactor；相关 P0/P1 未解决不交付该切片，P2 必须修复或由用户明确接受延期，P3 可排序。无关缺陷登记独立切片，不搭车重构。
- 默认复用现有服务、端口、模型、组件和测试。删除确认失效的实现与引用；不以抽象工厂、通用工作流、兼容层或第二套状态事实替代少量重复。
- 用户已批准实施已设计的修复与可行性验证；035 自动来源仍需 G3 证据，不因实施指令自动放开。禁止覆盖 App 未提交修改，生产停机、Secret 迁移和新机器操作须核对目标与前置条件。

## 2. 问题索引

| ID | 优先级 / 分类 | 问题 | 当前状态 | 修复切片 |
| --- | --- | --- | --- | --- |
| CQ-001 | P2 / 行为缺陷 | Web/App 对本地上传任务展示不可执行的下载重试 | 两端代码及组件回归通过，Web 合成浏览器通过；真机待验收 | 下载操作契约 |
| CQ-002 | P2 / 行为缺陷 | Web 视频上传缺少完成响应丢失后的幂等恢复 | 已修复，11 项传输测试与合成浏览器回放通过；真实存储待验收 | 上传恢复 |
| CQ-003 | P2 / 行为缺陷 | Web 任务多个查询入口可写回倒退版本 | 已修复，可控 Promise 及混合轮询/Socket 回归通过 | 任务状态收敛 |
| CQ-004 | P2 / 验证缺陷 | 并发重试测试的子类注入已脱离真实能力对象 | 已修复，真实 PostgreSQL 正/负对照 2 项通过 | 测试有效性 |
| CQ-005 | P2 / 行为缺陷 | App 不确定响应后的手动重试重新生成幂等键 | 已修复，受控失败/并发/会话单测通过；真实 API 待验收 | 下载操作契约 |
| CQ-006 | P3 / 重复规则 | 下载创建和展示重复解析 media_kind | 已关闭：最小去重与回归通过，ddb6b9fb | 下载元数据 |
| CQ-007 | P3 / 重复规则 | 剧本分析/改写复制同一输入完整性校验 | 已关闭：共享校验与原算法回归通过，dce813aa | 剧本输入校验 |
| CQ-008 | P3 / 重复规则 | Web 两套上传生命周期重复且恢复行为分叉 | 09f04da3 最小提取完成，其余相似编排裁决保留 | 上传恢复 |
| CQ-009 | 设计风险 / 非现有代码缺陷 | 035 可选来源维护者可能先于必要性证明落地 | 条件限制，未实施 | 035 G1–G4 |
| CQ-010 | P2 / 可访问性 | 封面占位辅助文字对比度不足 | 已关闭：浏览器复验通过，16516f5c | 恢复页 QA |
| CQ-011 | P2 / 验证缺陷 | 轮询假时钟未逐轮渲染，过度请求漏到真实网络 | 已关闭：84dfb5e5，受控次数与终态通过 | 测试隔离 |
| CQ-012 | P3 / 过度设计风险 | Web 公共目录混放业务 Hooks、接口类型别名和纯转发函数 | 已清理；类型检查、300 项测试与构建验证 | 前端目录职责 |

## 3. 证据、最小修复与验收

### CQ-001：重试入口必须区分远程来源和本地上传

证据：[RetryDownload](../backend/app/services/downloads/retry_download.py)第 60–61 行明确拒绝非 `remote_provider`；[Web 详情](../frontend/src/components/downloads/download-state.tsx)第 52–54 行、[Web 列表](../frontend/src/components/downloads/download-history-list.tsx)第 92–94 行、[App 详情](../../video-app/lib/features/history/presentation/download_task_actions.dart)第 106 行附近与 [App 列表](../../video-app/lib/features/history/presentation/download_history_item.dart)第 116 行附近只按 status/fileAvailable 决定重试。响应已有 source_kind，无需新建接口。

影响：本地上传取消/失败或文件已不可取时，按钮会调用必然被拒绝的远程重试用例。服务器的拒绝是正确边界，不能为了按钮“能点”而删除。

最小修复：两端各收敛一份来源感知的操作判定，列表/详情共用；本地来源提供明确重新选择文件/重新导入入口，不静默创建远程任务。跨语言通过契约样例对齐，不建设共享运行时规则引擎。

验收：两端列表和详情都覆盖 `remote_provider/browser_import × failed/cancelled/succeeded-without-file`；本地不调用 retryDownload，远程保留原行为；保留服务端拒绝测试。

### CQ-002：视频上传复用已提交的幂等结果

证据：[media-import.ts](../frontend/src/lib/upload/media-import.ts)第 57–75 行创建资源后无条件申请 upload session；[document-import.ts](../frontend/src/lib/upload/document-import.ts)第 86–91 行会直接返回 verifying/ready 结果；[CreateUploadSession](../backend/app/services/imports/service.py)第 190 行拒绝非 uploading。既有 [媒体导入测试](../frontend/tests/unit/media-import.test.ts)第 172 行附近只为文档覆盖“完成响应丢失”。

影响：视频 complete 已被服务端接受、客户端没收到响应时，以同一 key 再次启动会取回 verifying/ready 资源，然后错误请求上传会话，无法从已有成功提交恢复。不是存储故障，也不应丢弃幂等键重复创建资源。

最小修复：视频流程消费真实资源状态；verifying/ready 直接返回，其他终态明确引导，只有 uploading 才申请分片会话。先补视频对应负例，不先重写整个上传器。

验收：verifying/ready 重放只发创建资源的幂等查询式请求，不重新 PUT 或 complete；uploading 正常上传；failed/cancelled/expired 不冒充成功。

实施结果：新增 verifying/ready 及 failed/cancelled/expired 五项用例，先失败后通过；视频服务按服务端状态恢复原资源，仅 uploading 继续传输。`media-import.test.ts` 全部 11 项通过，未改变后端或资源授权。浏览器完整上传验收仍待完成，不能以单测关闭端到端门禁。

### CQ-003：Web 任务更新必须按目标、操作代次和版本收敛

证据：[useDownloadJob](../frontend/src/components/downloads/use-download-job.ts)第 69–106 行包含独立 Socket/轮询 GET，Socket 回调 await 后没有失效检查；[useAnalysisJob](../frontend/src/components/analysis/use-analysis-job.ts)第 74–114 行同样存在独立 GET，虽有 disposed 但都直接 setJob，没有响应 version 比较。两处 versionRef 用于订阅起点，不是写回保护；[task-socket](../frontend/src/lib/task-socket.ts)过滤事件版本也不能控制后续 HTTP 响应顺序。

影响：同一活动任务 v4 响应先返回、v3 后返回时，进度/状态可以倒退；下载的旧 Socket 回调还可能在切换任务或取消后污染新状态。此处是 Web 问题，不把 018 已修的 App 问题重新打开。

最小修复：集中同一 Hook 内所有状态接纳入口，检查目标身份、操作代次和单调版本；成功、失败、finally 都受保护。先修两个 Hook，再判断是否值得提取小型请求代次辅助，不创建通用任务框架；下载新 job 与分析同 job/new run 的语义保留。

验收：Socket/轮询乱序、同任务版本倒退、取消/删除后迟到成功与失败、切换来源后旧请求返回均有可控 Promise 回归；新状态和操作错误不被旧请求覆盖。

### CQ-004：故障注入必须命中真正执行对象

证据：[test_retry_admission.py](../backend/tests/unit/infrastructure/analysis/test_retry_admission.py)第 48–58 行在 `SqlAlchemyAnalysisRepository` 子类覆盖 `_require_retry_capacity`；[当前组合入口](../backend/app/repositories/analysis_repository.py)最后两行把 retry_job_and_enqueue 绑定到独立 `AnalysisRetryRepository` 实例；[实际调用](../backend/app/repositories/analysis_repository_retry.py)第 54 行调用的是该实例的校验，不是测试子类的方法。

影响：测试中声称“读计数后暂停”的 sleep 不会执行，预期交错不受控制；最终计数断言仍有价值，但不能证明指定竞态已被覆盖。未据此宣称生产锁失效或测试必然失败。

最小修复：在真实能力调用边界设置可观测同步点，并断言注入确实执行；保留实际 PostgreSQL 事务和 owner 锁。不要恢复已移除的继承结构来迁就测试，也不要单靠 sleep 猜调度顺序。

验收：测试证明实际校验路径被命中，受控并发最终只有一个新 run；使用隔离测试变体去掉关键锁后应稳定暴露预算竞争，恢复锁后通过。不能要求两个持锁事务同时抵达锁内 barrier 而制造死锁。

实施结果：先增加调用次数断言，得到 `0 != 2` 的稳定失败；改为在实际 AnalysisRetryRepository 上注入可计数校验及有界并发 barrier，不再覆盖组合入口。真实锁保留一个新 run，隔离负对照去锁后得到两个，2 项通过。使用现有 PostgreSQL 的临时 schema，夹具自动清理，未更改生产锁或业务表。修复提交以本段对应 Git 历史为准。

### CQ-005：App 幂等键应属于一次逻辑重试操作

证据：[download_history_repository.dart](../../video-app/lib/features/history/data/download_history_repository.dart)第 79–85 行每次 retry(jobId) 新建随机 key；两处 Widget 捕获错误后恢复按钮，再点击会重新调用该方法。相比之下，[Web 列表](../frontend/src/components/downloads/download-history-view.tsx)第 74–80 行和 [Web 详情 Hook](../frontend/src/components/downloads/use-download-job.ts)第 132 行附近在不确定失败后保留 key。服务端 RetryDownload 以原任务和 key 创建新任务，同源不同 key 可创建不同资源。

影响：服务端已经创建任务但响应丢失时，App 再点击会创建第二个任务并重复占用预算。当前认证层内部重放复用闭包中的同一个 key，这条路径不是本项缺陷。

最小修复：在应用操作状态中保存 owner/session + 原任务 + 逻辑操作的 key；不确定失败复用，确认完成或用户发起新逻辑操作后更新，退出/切账号清理。不能给每个 job 永久固定一个 key，也不引入持久数据库或全局无限缓存。

验收：服务端提交后丢响应，再点击使用同 key、得到同新任务；新操作得到新 key；切换账号不继承旧 key；列表和详情行为一致。

### CQ-006：只提取确实相同的 media_kind 规则

证据：[create_download.py](../backend/app/services/downloads/create_download.py)第 115–122 行与 [views.py](../backend/app/services/downloads/views.py)第 234–241 行 `_media_kind` 完全相同。同文件相邻 `_asset_count` 却分别要求正数与非负数，不能视为完全重复。

影响：媒体类型扩展/非法数据处理需要双点修改。尚无该重复已造成线上错误的证据。

最小修复：放到现有 downloads 业务内聚的校验模块，保持默认值、异常种类不变；先追踪 asset_count 的图集/视频调用语义，不合并其不同约束，不引入新的通用元数据 DTO。

验收：缺字段、有效枚举、非字符串、未知枚举产生与原调用方相同结果；视频零资产与图集正资产边界保留。

### CQ-007：共享输入完整性规则，不合并两种分块算法

证据：[screenplay_analysis_plan.py](../backend/app/services/analysis_execution/screenplay_analysis_plan.py)第 76 行起与 [screenplay_rewrite_plan.py](../backend/app/services/analysis_execution/screenplay_rewrite_plan.py)第 109 行起 `_validate_source` 相同。分析按场景聚合，改写可拆场景且绑定哈希，输出模型不同。

最小修复：仅收敛同一服务内的来源完整性函数；不做可配置的“万能分块器”、共同基类或 strategy registry。任何新增边界校验应单列行为变化，不能夹在等价去重里。

验收：两入口对空文本、CR/NUL、末尾换行、重复场景 ID、不连续场景和尾端不匹配的错误一致；既有分块输出、文本覆盖、哈希及资源上限不变。

### CQ-008：上传生命周期去重必须先讲清差异

证据：[useMediaImport](../frontend/src/components/intake/use-media-import.ts)、[useDocumentImport](../frontend/src/components/intake/use-document-import.ts)重复维护 ActiveRun、StableKey、取消与进度；[两类服务](../frontend/src/lib/upload/media-import.ts)和[文档服务](../frontend/src/lib/upload/document-import.ts)还复制 phase/observer 及传输编排。文档有失败取消和已完成恢复，视频有 declared_origin 与取消通知，不能简单互相替换。

最小修复：先解决 CQ-002 并明确取消/完成竞态，再只提取相同的操作身份和传输生命周期，具体资源 API、格式校验及失败策略保留在各自服务。继续复用已有 `lib/media-upload`；如果小型提取仍需大量模式开关，保留局部重复并记录理由。

验收：两个流程都覆盖取消、卸载、创建响应迟到、完成响应丢失、失败重试及稳定 key；检查没有吞掉原错误或新增第二套上传底层。不是以减少多少行作为通过条件。

### CQ-009：035 可选架构不得先于必要性证明

证据：[035 设计](design/035-平台访问与会话恢复能力设计.md)第 6 节定义了来源维护者、持久 envelope 和操作租约，但第 11–13 节明确自动来源未证明、可放弃；这是设计中的潜在复杂度，不是已经存在的冗余代码。

处置：先用现有 manual_file/引擎/出口完成 G1/G2；只有 G3 证明单个平台必须且能够安全维护来源才批准 I2。没有 Go 不生成占位模块、空端口或全平台 sidecar。路径冷却/repair 字段也必须有失效重试实验支持后才引入。

验收：G4 提交“保留/修改/删除/不引入”清单；每个新进程、字段和抽象对应明确需求、失败场景和测试。仅文件来源足够时，明确不实施来源维护者。

### CQ-010：封面占位文字的对比度不足

证据：2026-09-12 agent-browser 对候选构建 390px 浅色下载失败页运行 axe，`media-cover.tsx` 的“暂无封面”使用 background/45，实测前景 #767676、背景 #0a0a0a，4.35:1 < 4.5:1。此前未因截图肉眼正常而发现。

最小修复：同一语义色改为 background/70，不新增 token 或重做封面。验收：390/1280px 明暗四次检查全部 0 violations / 0 incomplete，已检查截图；修复 `16516f5c`，详见根设计 QA。

### CQ-011：轮询测试的时间推进必须符合真实渲染周期

证据：`analysis-panel.test.tsx` 的 degraded 轮询测试一次推进 30,001ms，React 在 act 结束前未提交完成状态，有限的 HTTP mock 被耗尽后漏到 localhost:3000；全量 261 项通过仍出现 ECONNREFUSED，不能将其解释成被测平台失败。

最小修复：两个有界轮询周期分别 act，第二个响应为 succeeded，并精确断言两次刷新与完成态。没有吞日志、放宽业务逻辑或改生产轮询。13 项面板测试及全量回归通过且连接报错消失；修复 `84dfb5e5`。

## 4. 已审查但不应机械删除的结构

- 下载与分析的 Repository 组合：承担不同事务和任务模型；不因有多个能力对象就报过度设计。CQ-004 应修测试注入，不反向恢复继承。
- [DownloadExecutionRepository](../backend/app/repositories/download_execution.py)：含错误语义转换和 ArtifactCreate 映射，不是已证实的空转发层；是否去掉须先证明这些边界另有唯一所有者。
- Web/App 的端侧呈现和状态模型：不同语言/生命周期，需要契约一致，不要求共用一份可执行 UI 代码。
- 生成客户端、Protocol 与实现的同名签名、SQL/ORM 必须一致的字段以及 UI import 列表：不作为复制缺陷，也不手改生成文件“去重”。

## 5. 修复顺序与未覆盖范围

1. 在批准修复后，先修 CQ-004 的验证有效性，并为 CQ-001/002/003/005 补稳定失败测试；修复顺序按实际影响，不以去重率排序。
2. 分别交付下载操作、上传恢复、任务状态收敛的小切片；App 在它自己的仓库内实施，不顺带提交用户现有修改。
3. CQ-006/007 可独立做等价重构；CQ-008 在上传行为稳定后再决定抽取；CQ-009 依 035 门禁裁决。
4. 后续扩大到账号/管理、AI/报告、存储清理、配置/依赖和容器时继续在本文登记，不新建重复问题平台；本轮未完成这些区域的全面审查。

## 6. 本轮验证记录

2026-09-12 运行现有 Web 测试：

```bash
npm test -- tests/unit/media-import.test.ts tests/unit/media-import-page.test.tsx tests/unit/download-job-hook.test.tsx tests/unit/analysis-job-hook.test.tsx tests/unit/history-page.test.tsx
```

5 个文件、20 项测试通过。它们是原有覆盖基线，不包含上述新增负例，因此所有缺陷仍未关闭。未新增/修改业务代码或测试；未运行数据库并发故障注入、Flutter/浏览器真机、真实平台和部署验证。后续关闭记录必须追加实际修复与验收结果，不把本轮通过当修复证据。

文档静态检查：7 个变更文件、154 个相对链接存在；035 的 15 项需求/21 项验收引用合法，9 个 CQ 索引与正文一一对应；两处被列为完全重复的函数已逐块比较相同。diff 空白检查通过，变更白名单不包含业务源码。

## 7. 首批实施与验证（2026-09-12）

以上第 6 节为初次审查基线，不代表当前仍未实施。当前结果如下：

| 切片 | 实现与证据 | 剩余边界 |
| --- | --- | --- |
| CQ-001 | Web 16516f5c，App 工作区；两端来源判定共用，三种本地终态列表/详情无 retry；Web 真实浏览器合成数据验证返回首页及远程按钮 | 不是实机媒体保存播放验收 |
| CQ-002 | 72b8adbf；五个新状态负例先失败后通过，媒体传输共 11 项；浏览器选择合成文件，创建返回 verifying 后直接进入原任务，无上传会话/complete/PUT | 浏览器验证为合成服务响应，未做真实存储响应丢失实验 |
| CQ-003 | ad671da6；目标/操作代次/版本保护全部接纳入口，包含成功、错误与 finally；取消、删除、切目标及查询乱序回归 | 不新增通用任务框架；发布环境 Socket 仍待验收 |
| CQ-004 | 9e31bba7 + 9e3b7d8a；真实 PostgreSQL 临时 schema 的持锁/去锁正负对照，均证明校验注入被命中 | 不更改生产锁或业务表 |
| CQ-005 | App 工作区 DownloadRetry；丢响应复用 key、成功后新 key、并发 single-flight、账号 generation 隔离回归 | 只在当前挂载操作作用域内保持 key；不宣称跨 App 重启恢复或真实 API 故障注入已通过 |
| CQ-006/007 | ddb6b9fb / dce813aa；共享规则新增 27 项，连同现有 planner/worker 聚焦 50 项通过；asset_count 与两种分块算法保留 | 等价重构，不附带新校验边界 |
| CQ-008/009 | 09f04da3 共享 phase/observer/error/abort；具体上传 Hook/API/取消策略保留，不引入来源维护者、空模块或通用编排框架 | CQ-009 条件限制继续有效，G3 未获 Go |

后端全量 1688 passed / 2 skipped；跳过项分别是未提供隔离 MinIO 的边界集成测试、macOS 不具备的 Linux O_PATH 行为。Ruff 检查/格式通过，mypy 528 个源文件无问题。App analyze 无问题、全量 199 项通过、Android debug 与 iOS simulator 构建通过；插件未来 SPM/Kotlin 迁移提示仍保留。

Web lint/typecheck/format 与生产构建通过；最终全量 60 个文件、263 项通过，其中乱序测试 16 项，未再出现连接报错。浏览器使用 agent-browser 隔离会话、独立候选前端和合成响应，不使用真实账号或平台来源。前述 UI 与单测不能关闭 035 的 G1/G2/G3/G5；本轮未更新生产、Tailscale、手机或凭据，未推送远端。App 保留未提交变更且不搭车提交原有改动。

## 8. 平台策略与诊断切片的复杂度裁决

- 已修复：端点存在性隐式决定默认权限；默认值改为经过目录校验的显式策略，inspection 指纹包含所选策略。验证缺少端点时不会调用另一路线，改变策略不会重放旧结果。
- 已合并：状态投影不再逐字段复制 ProviderStatusView，使用不可变 replace 保留新增契约；平台 hostname 只由后端目录下发，Web/App 不再维护平行匹配白名单。
- 已复用：Flutter 策略选择使用 AppDropdownField，仅增加 option.enabled；保留用户已有下拉组件布局改动。Web 使用现有 Radix Select/Button、稳定 services 入口。
- 有必要新增：30 秒状态 single-flight，减少同进程并发状态查询重复 DB/RPC；有取消/失败/过期并发负例。此缓存不充当授权事实。
- 不引入：同命令的重复 Profile、第二个任务模型、账号池、自动登录、没有 G3 证据的来源维护者和占位 repair_count；持久冷却独立按 I3 验证，不能用状态缓存替代。

## 9. 持久冷却切片审查

- CQ-010 / P1 / 已修复并回归：预领取后固定探测超时可能越过租约。租约返回实际 expiry，探测预算取剩余租约减 5 秒与 30 秒的较小值；签名截止同时在 Runner 执行。覆盖临期不发请求、预算不重置、运行超时取消清理。
- CQ-011 / P1 / 已修复并回归：半开下载仅在 metadata 返回后检查旧 context，可能先使用新来源。InspectRequest 传入冻结 context，Runner 在访问前验证，操作文件仍使用原有修订校验；覆盖旧 context 零外部调用及 HTTP 参数传递。
- 必要结构：唯一新增冷却表跨任务持久，无 job 外键；关闭后保留单调 version 避免 ABA。复用既有 job、Outbox 和 retry_at，不新增任务框架、后台刷新队列或空 repair 字段。
- 保留边界：状态快照最多 30 秒，仅展示；准入每次读持久状态。短事务不跨 RPC，数据库锁超时失败关闭。20 并发/200 次是本地数据库准入测量，不是全 HTTP 或多机 HA 结论。
- 尚未解决的部署验证项：egress_affinity 绑定配置出口而不是实测公网 IP；同配置换物理出口必须重新做迁移验收，不能据此声称自动识别公网变化。自动来源、全平台与新机仍受 035 门禁约束。

## 10. 固定矩阵与部署说明修复

- CQ-012 / P2 / 已修复：fixed_matrix 先过滤未知 provider，混合已知/拼错名称可能只测已知子集仍返回成功。新增 runtime 创建前全集校验，未知项退出 2 且零外部调用；已知单项执行/资源关闭/不输出 URL 有回归。
- CQ-013 / P2 / 已修复文档：schema 顶部仍说 Compose 每次启动自动初始化、换机手册仍暗示缺 operator 自动走匿名。改为当前态 SQL 由部署者按需应用，访问策略显式，更新必须同版重建；保留既有 fixed_matrix 命令，不新增重复诊断 CLI。
- CQ-014 / P1 / 已修复：生产私有 `.provider-sessions` 与 `.provider-secrets` 只在 Git 忽略，Docker 上下文未排除。补充递归目录排除和契约测试；没有读取真实会话内容，没有将私有来源复制进镜像。镜像显式 COPY 原先未引用这些目录，本项修复的是构建上下文暴露，不声称曾泄漏到发布镜像。

## 11. 实际用户链接暴露的部署缺陷（2026-09-13）

- CQ-028 / P1 / 阻断未解除：用户截图确认视频号与 Reddit 的 Chrome 文件下载均为“已被您的组织屏蔽”。后台文件存在和播放成功不能证明设备落盘。前端状态候选已区分“服务端已完成”与设备保存，三类媒体不误报回归通过；保留原鉴权同源流，不增加绕过策略的下载路径。常见本地配置未找到 DownloadRestrictions，但实际生效策略尚未取得，浏览器工具拒绝访问 chrome://policy；已请求用户提供条目和值/来源。待策略归因、授权纠正及原浏览器文件/哈希验收后才能关闭，不能以文案修复代替解除拦截。

- CQ-023 / P1 / 本机已修复：抖音/Reddit 限定 Chrome 会话存在，但生产 Runner 未启动且配置为缺失的文件来源。复用现有加密代理并持久启用 profile/默认策略；两平台完整探针、Runner 重建后及 8101 浏览器任务均通过，证据见 035 验收第 19 节；不将本机来源当新机已登录。
- CQ-024 / P1 / 已修复：单个宿主代理串行执行所有平台导出，元宝慢操作阻塞后来到达的 probe/其他平台导出，实际导致抖音页面 503、Reddit 探针超时。改为每平台一个有界导出，主线程继续处理 probe，空闲平台处理新请求；两项阻塞回归先失败后通过，实际元宝失败时 Reddit metadata/media 与抖音业务恢复。没有增加进程服务、账号池或兼容回退。
- CQ-025 / P1 / 本机来源修复已验收：普通 Chrome 的元宝登录仅复制 Cookie 无法恢复。按用户明确批准替换为独立持久元宝来源，不复制个人 Profile；首次由用户登录，后续每次重新启动浏览器导出单操作租约。来源持久化、权限、互斥、失败释放锁和登录字段类型回归通过；实际 metadata/media、API/Worker/Runner 重建后的 8101 任务 `707a2a06-a2c6-4a7d-9cbd-fd1eaae0e0eb` 完整文件和浏览器播放至结尾通过。此项只关闭本机来源缺陷，初次平台请求失败、其他平台抖动、账号切换与新机范围不包含在本项结论中。
- CQ-026 / P1 / 已修复：元宝临时 Chrome 另建进程组，外层导出超时强杀时可能脱离统一清理。改为继承导出进程组；启动参数回归先失败后通过。此修复保证取消边界，不代表元宝授权恢复。

- CQ-027 / P1 / 待归因与持续性验收：本次视频号首轮 metadata/media 分别 21003/19329 ms 返回 provider_temporarily_unavailable，随后同来源完整探针与真实任务成功；抖音回归出现一次 inspection_failed（3185 ms），同轮媒体成功且单独解析复测成功（4055 ms）。会话读取成功不能掩盖请求间歇失败。保留初次失败证据，后续以安全阶段诊断定位平台请求/探测/总预算，补有界重试或错误归因的确定性测试；不得凭复测成功宣称高可用或增加账号/线路回退。

- CQ-019 / P1 / 本机 YouTube 切片已修复：生产默认文件来源未准备，已安装按需助手没有被该拓扑使用，匿名线路被要求登录。增加仅 YouTube 的 Compose 来源覆盖、持久默认策略与精确启用说明，复用既有有界加密租约。68 项聚焦回归及原视频两次真实文件（含 Runner 强制重建）通过，不新增浏览器框架；其他平台仍分别验收。
- CQ-020 / P1 / 待专项修复与验收：既有 ProviderSessionStore 动态来源将 `credential_version_id` 固定为 browser，不能据此区分 Chrome 主体变化；文件来源有 keyed revision，动态来源没有相同保证。后续需明确同账号轮换与主体变更的识别，覆盖解析后换账号必须拒绝旧 context、Cookie 正常轮换和撤销测试；本轮不放松冻结校验，也不声称账号切换或迁移通过。
- CQ-021 / P1 / 修复验证中：Vimeo 固定样本声明独立音轨但 acodec 缺失，Runner 先接受可用纯视频，跳过音轨探测，导致 8101 生成静音制品并显示成功。复用有界探测补齐音轨，不猜编码、不缩短原时长；无法确认音轨时禁止静音误成功。需确定性回归及真实音视频交付后关闭，旧静音制品不改写。
- CQ-022 / P1 / 待修复：红果固定样本的 ffprobe 间歇返回 `Server returned 5XX Server Error reply`，稀疏格式补齐吞掉探测失败后对外归为 format_unavailable；重复 inspect/download 已确认可成功生成完整文件，不能据此永久认定格式不支持。需保留临时上游故障归因并评估原线路有界重试，覆盖部分格式可用、全部探测失败和总 deadline；不得以放宽计划匹配或换线路掩盖失败。

- CQ-018 / P2 / 已修复：链接入口向普通用户暴露访问策略、会话和证据细节，并为了选择器订阅平台状态、重复解析 URL 域名；配置了但未运行的受控端点还会成为隐含默认依赖。删除整套 Web 选择器及其状态/请求/提示函数，而非 CSS 隐藏；服务端复用现有部署默认和准入规则，允许公开访问的平台未覆盖时默认 public。入口、幂等、显式受控默认回归及 8101 真实页面验证通过，后端 1739/Web 283 项通过。此项仅关闭入口过度设计，不关闭实际 YouTube 下载故障或移动端收敛。

- CQ-015 / P1 / 已修复：Next.js standalone 构建期 rewrites 固定后端地址，候选 frontend 的运行时 BACKEND_ORIGIN 被忽略；用户新页面实际调用旧 API，策略缺失且失败被旧链路泛化。复用已有 proxy 运行时外部 rewrite，移除重复构建地址，不读取凭据或请求体。回归先 10 项失败后通过；Web 280 项、构建、lint/类型/格式及 23 项部署契约通过。真实已登录页面会话保持，策略出现，新 API 日志确认 GET/POST 到达。仅修复路由，不宣称该 YouTube 视频可下载。
- CQ-016 / P1 / 待修复：镜像构建提示依赖公告；`npm audit --omit=dev` 确认 next 16.3.0 的 critical 公告 GHSA-p293-qw3h-jr36、GHSA-2xp9-vwfh-vxw4，sharp 的 high 公告 GHSA-rgj7-g3m4-5g8c。当前候选为 Linux 且 images.unoptimized=true，不据此宣称已受攻击或所有利用条件成立；仍需独立升级受影响依赖、重新生成锁文件并完成全量/镜像/页面回归，再关闭该项。本次未更改依赖或自动执行 audit fix。
- CQ-017 / P1 / 已修复：真实 Chrome 发出的 `/api/auth/me/` 经代理到 FastAPI 后返回 307，Location 指向内部 `http://api:8111/api/auth/me`，导致外部浏览器无法恢复登录。代理将 API/health 尾斜杠规范化为后端真实路径，不重定向浏览器、不读取请求体或复制 Cookie。三个负例先失败后通过，全量 Web 283 项与构建通过；8101 的同一路径不再返回 Location，用户原 Chrome 会话无需重新登录即恢复。这里只证明登录和路由恢复，不证明 YouTube 文件交付。

## 12. 重启可靠性与登录误归因（2026-09-15）

证据基线与完整方案见 [021 深度调研](research/021-下载可靠性与重启会话故障深度调研.md)。优先级沿用本登记定义；共同出口故障为本轮最先处置项。

- **CQ-029 / P1 / 行为与验证缺陷 / 已修复**：Squid 前台 PID 1 将 PID 文件写入无 tmpfs 的容器 `/tmp`，异常停止后残留文件导致重启持续退出。修复 `500c1a71` 为两个业务 Compose 的代理 `/tmp` 增加受限 tmpfs，保留 PID 健康检查和现有 ACL。契约测试先失败后通过，34 项聚焦回归及两套 Compose 解析通过；同镜像完整配置候选与生产容器均完成正常停止/start 3 轮、SIGKILL/start 3 轮。生产代理保持原镜像，公网转发成功、私网目的地址被 403 拒绝，四个当前运行的受控 Runner 与公共 Runner 全部恢复健康；B站匿名 metadata/media、抖音 operator_managed metadata/media 固定矩阵全部通过。该项关闭公共出口的重启循环；浏览器本地保存、九平台完整矩阵及缺失 Operator 仍按 CQ-028/CQ-031 独立验收。
- **CQ-030 / P1 / 行为与验证缺陷 / 已修复**：provider_errors 的全局 Fresh cookies 规则忽略 authenticated 状态，将抖音空 detail/JSON 失败直接映射为需要登录；混合限流或登录提示亦有歧义。修复 `29d2cf05` 将抖音模糊 Fresh cookies 限定为 provider_temporarily_unavailable，将明确 429 与模糊混合提示分别映射为 rate_limited/temporarily_unavailable；明确 Cookie 过期、Vimeo/微信视频号等确切认证要求及内容权限规则保持原分类。四项红测转绿，相关 127 项与后端全量 1616 项通过；目标文件 Ruff/mypy 通过。新镜像部署到公共及四个当前启用的 Operator Runner 后全部 healthy，容器内验证匿名/已认证模糊输入均返回 503，明确过期仍返回 credential_expired。抖音 Runner 重启后未重新导出会话，operator_managed metadata/media 分别成功；B站匿名 metadata/media 亦成功。由此关闭本项服务端误归因；全量 mypy 的 3 个既存 Settings call-arg、浏览器提示文案与 CQ-031 实例完整性独立保留。
- **CQ-031 / P1 / 运行与验证缺陷 / 本机生产已修复**：旧部署引用已不存在的临时 images.yml；API/Worker/Canary 配置九条受控路线但仅四个 Operator 运行，Canary targets 为 0。修复将本机私有生产配置收敛为 YouTube、抖音、Reddit、微信视频号四条已有来源且运行中的受控路线，无来源的五条 endpoint 从允许集合移除，不隐式切换其他账号；Canary 配置 5 个平台各 metadata/media 共 10 个真实目标。提交 `29d2cf05` 的统一镜像保留发布与回滚标签，API、前端、Worker、Canary、公共 Runner 及四个 Operator 已用仓库内 prod/browser 两份 Compose 重建，容器标签不再引用临时文件，健康与 HTTP 检查通过。首轮/最近一轮 10 个 Canary 目标全部 succeeded。该项关闭本机配置/实例漂移；另外五个平台只有准备合法来源并启用对应 profile 后才能宣称受控路线可用，23 平台完整矩阵仍需独立维护。

CQ-020 动态来源身份修订、CQ-027 间歇平台请求、CQ-022 红果探测和 CQ-021 音轨问题仍独立保留；本次研究不借旧文档的单次成功关闭这些项。

## 13. Web 下载触发不得重建认证应用（2026-09-15）

- **CQ-032 / P1 / 行为缺陷 / 本机生产已修复**：Web 在取得短时下载地址后创建临时 `<a>` 并直接 click，且没有独立浏览上下文。部分浏览器把同源附件响应作为当前文档导航，导致根布局与 `AuthProvider` 重建，页面显示“正在恢复登录状态”；这不是服务器要求重新登录。修复改为一次性隐藏 iframe 承载同源附件请求，当前页面和内存会话保持原位，60 秒后回收节点；不把大文件读入 Blob 内存，也不新增标签页或绕过浏览器下载策略。回归测试先观察到 anchor click 的稳定失败，再验证不触发顶层 anchor、下载 iframe 已创建、当前详情路由不变且节点按时回收。前端 format、lint/typecheck、63 个文件 287 项测试及生产构建通过。提交 `567e3215` 的镜像只重建 frontend 后健康；原已登录 Chrome 在下载记录和任务详情各点击一次，URL、账户菜单和完整业务内容保持，未再次显示认证恢复；API 两次都只收到 download-url 与 file 请求，期间没有新增 auth/me。CQ-032 关闭；浏览器策略及设备文件落盘继续由 CQ-028 验收。

## 14. 会话来源与跨机依赖（2026-09-15）

- **CQ-033 / P1 / 配置与平台验证缺口 / 挂载代码已修复，平台未通过**：五个 Chrome operator 缺少宿主加密队列挂载，`a3892575` 已补齐并通过 31 项契约及远端 CI。小红书候选真实解析仍在来源阶段失败，已停止且未加入默认路由；挂载通过不代表五平台已支持。关闭范围必须分别记录配置修复、有效来源、默认入口和完整文件证据，见 035 验收第 27 节。
- **CQ-034 / P1 / 来源所有权与诊断缺口 / S0 已修复，S1 部分通过，换机未完成**：`31f0811e`/`cd1570b4` 已区分来源缺失、权限拒绝与账号缺失并完成 endpoint 预检，原 121 项聚焦回归通过。后续 TCC 已证实本次采集进程归属 VS Code，开启实际执行宿主授权后既有 Chrome 来源可读，详见 CQ-043。YouTube/抖音/Reddit 生产已改为单平台只读文件，候选完整媒体和重启通过，YouTube 正常网页任务已持久化并全片解码。此项验收时 YouTube 维护仍依赖显式采集；后续本机维护试点见 CQ-044。真正第二机器、三次干净恢复、跨多次真实轮换与撤销等 T23–T27 范围尚未全部验收；动态身份修订继续关联 CQ-020。
- **CQ-035 / P1 / 验证路线缺陷 / 已修复**：小红书固定公开样本被统一指定为 operator，导致不可读的 Chrome 来源遮蔽匿名提取能力。生产匿名对照在同一样本上取得 metadata 2962 ms、完整 media 6214 ms 成功；`f0184c2d` 将固定矩阵改为 `anonymous`，不再为该公开样本领取 Chrome 来源，并增加回归防止再次误绑。67 项目录/固定矩阵/Runner 聚焦回归通过。镜像 `sha256:f5a54168779b462ee250dd6bee2d9dfe3a0d20d051f4e7124363c48325acdd55` 重建 Canary 和匿名 Runner 后，标准矩阵再次取得 metadata 2159 ms、完整 media 5224 ms 成功，关闭固定路线及重启复测范围；短链接、图集、访客画质、账号内容和全部小红书链接仍不在证明范围。
- **CQ-036 / P1 / 多平台验证路线缺陷 / 已修复**：固定公开矩阵仍从“平台存在浏览器会话策略”推导 X、Instagram、Facebook、Pinterest 必须使用 operator，导致四个平台受日常 Chrome 权限影响且生产周期监控缺席。同链接生产匿名对照的 metadata/media 均成功：X 12837/27449 ms、Instagram 7861/16667 ms、Facebook 5461/9870 ms、Pinterest 2473/25288 ms；Reddit 匿名两阶段均为 `provider_auth_required`，YouTube、抖音、视频号 metadata 分别为 `provider_verification_failed`、`provider_temporarily_unavailable`、`provider_auth_required`。`2cca58b1` 将成功的四平台固定路线改为 anonymous，并把全部九个会话能力平台分入“已证明匿名”或“当前保留 operator”两个显式集合；以后新增平台必须明确归组。后端全量 1785 passed / 2 skipped，Ruff/格式及 mypy 534 个源文件通过；跳过项仍为隔离 MinIO 未提供和 macOS 不具备 Linux `O_PATH`。生产周期 Canary 扩为 20 个目标/10 个平台；镜像 `sha256:76639ce0f41d579827b25e11189d859bcc396978623af44553223abd49629a6e` 重建 Canary 与公开 Runner 后，四平台八项标准矩阵再次全部成功，关闭本项。

## 15. 内容创作链设计审查（2026-09-15）

本轮依据基线 `f547b9e4` 与 [023 调研](research/023-内容创作与平台发布能力调研.md)。以下分清现有行为缺口、新需求和外部接入风险；初轮仅调研，后续已修复项及证据逐项更新。036 不关闭 035 的来源/换机问题。

- **CQ-037 / P1 / 证据回看行为缺口 / 已修复并完成候选浏览器验收**：`analysis-panel.tsx` 的完成态和旧报告均接通 Vidstack 定位；文章 evidence 改为可访问按钮。播放器就绪后才启用，加载失败/源文件清理保留准确说明；定位按真实时长限界，滚动并将焦点交给播放器，不自动播放。44 项聚焦回归、前端 63 文件/296 项全量测试和 lint/format/build 通过。候选 8125 页面使用隔离 API 夹具和真实 62 秒测试视频，分镜与文章点击后均观察到 `video.currentTime=30`，焦点进入播放器；390/1280/1920px 无横向溢出。关闭本 Web 行为缺口，不包含 App、真实模型/Provider 与全平台验收，见 036 验收第 5 节。
- **CQ-038 / P1 / 新需求下的内容生命周期缺口 / 待实施**：已有 `video-to-article` 与不可变报告，但没有持久可编辑作品、内容修订/图片页序、平台正文投影。原纯视觉分析约束本身不是故障；新文章/小红书生产需要创作证据与编辑/导出链。按 036 S2–S5 实施，不能用重新分析替代编辑，不能覆盖原报告事实。
- **CQ-039 / P1 / 发布接入设计风险 / 未接入，待门禁**：现有 `ReportPublisher` 只物化报告。外部公众号 Skill 的 `draft/add` 与小红书 MCP 无帖子 ID的成功响应不能直接映射“已发布”；需新增独立连接、确认版本、提交标记、未知结果和回执核对。此项记录计划接入必须满足的约束，不表示当前生产已发生重复发帖。按 036 A12–A20 分项验收。
- **CQ-040 / P1 / Skill 产品化边界 / 设计完成，待实施**：已有 loader 仅接受受限方法资源且已有指令 hash。外部 Skill 依赖脚本、宿主工具、文件配置和嵌套 references，不能为方便安装而开放任意脚本/浏览器权限。按 036 A00 固定上游归属/版本/许可，纯方法移植与工具适配分开，增加结构/质量门禁；未经逐文件审查的子 Skill 保持候选。

- **CQ-041 / P1 / 完成态操作错误丢失 / 已修复**：视频分析成功分支提前 return，未呈现 Hook 的 `state.error`，重新分析或删除失败时页面仍只显示成功报告。补齐成功分支错误提示，保留已有结果；失败重试和删除均有回归，候选浏览器真实触发 503 后显示“操作未完成”和本地化原因。剧本完成态此前已有提示，未重复改造。
- **CQ-042 / P1 / 报告导出导航遗漏 / 已修复**：CQ-032 覆盖媒体下载，但视频/文章/剧本报告与旧报告导出仍为直接链接。新增小型共享报告链接组件，保留 href/键盘语义，点击统一用现有 `triggerBrowserDownload`，阻止当前文档导航；不新增 Blob 大文件加载或下载协议。完成态、旧报告、剧本报告回归通过；候选浏览器附件响应后文档标记、路由、播放器 30 秒位置保持，未重复 auth/me。真实平台文件落盘与浏览器组织策略继续由 CQ-028/035 独立验收。

- **CQ-043 / P1 / 已登录 Chrome 与采集进程授权错位 / 本机权限归因和显式采集已修复**：TCC 实证责任进程为 Visual Studio Code，原 ChatGPT FDA 不能替代；用户开启实际执行宿主授权后，同一已登录 Chrome 的 YouTube/抖音/Reddit 按平台采集成功，无需登录测试浏览器。`03fd5b1e` 提供 capture-chrome/import/check 与原子发布；56 项聚焦回归及全量 1793 passed / 2 skipped。`2394541c` 的生产三文件 Compose 覆盖清除 sync 环境键，仅挂载对应只读文件；11 项部署契约通过，两次提交 CI 成功。YouTube 正常网页新任务 e657507d-cb08-489b-a911-389bc57fe539 已完整持久化、哈希和全片解码通过；此项只关闭本机权限归因与采集能力，不关闭 CQ-034 的独立维护/新机，也不关闭 CQ-028 设备保存。
- **CQ-044 / P1 / YouTube 静态会话轮换 / 本机项目生命周期已修复**：同一已验证来源曾被上游两次判定过期，本地文件校验仍通过，确认一次性快照不能持续。新增仅限 YouTube 的宿主维护进程：从已获 TCC 授权的实际桌面宿主启动，先同步采集，随后每 60 秒在用户请求之外有界读取现有 Chrome；变更通过既有域/字段/过期/文件安全校验后原子发布，失败保留旧来源，状态和 PID 文件均为 0600，输出不含 Cookie、路径或 revision。实测直接 `launchd` 子进程无法继承 VS Code FDA，已删除该无效路径；脱离启动宿主的维护进程父 PID 为 1，并完成第二周期 `unchanged`。生产来源 revision `d7dd2bd14bea…` 后固定 YouTube metadata/media 成功；重启 Operator Runner 后再次成功。已登录 8101 创建任务 `c7817c5e-3cd3-4eef-b5e8-b312f8f50cff`，51,933,107 bytes、564.431 秒、H.264/AAC、SHA 匹配、全片解码退出 0；点击获取文件前后 URL/标题/就绪状态保持且未出现认证恢复。本项关闭 Cookie 轮换导致的项目/容器重启与请求期反复采集；整机冷启动后仍须从已授权宿主执行幂等 `start`，第二机器和跨多次真实轮换由 T23–T26 继续验收。
- **CQ-045 / P1 / 腾讯视频完整媒体重新解析超时 / 待修复**：`agent-browser` 匿名访问固定样本可见播放器、剧集和会员全集，生产 metadata 18007 ms succeeded，但同轮完整 media 在重新解析阶段 120048 ms 返回 `inspection_timeout`。这不是来源缺失证据；需对同一固定链接分段记录 extractor、权益/DRM 判定和重新解析预算，补免费非 DRM 单集与明确会员/DRM 负例。不得以通用 Cookie、单纯放大超时或浏览器页面可播放来宣称支持。
- **CQ-046 / P1 / Compose 会话覆盖与无效 Runner / 已修复**：生产实际容器原由 prod/browser/session-files 三层配置混合创建；最后一层为清除前一层残留的 Cookie sync 重复了三个 Runner 的完整环境。小红书、X、Instagram、Facebook、Pinterest 已有完整匿名媒体证据，但两套业务 Compose 仍声明无默认路由的受控 Runner。现已收敛为单一 `docker-compose-prod.yml`，前三个当前文件平台直接只读挂载、视频号保留专用动态来源，删除两层覆盖与五组无依据 Runner；来源采集工具继续独立保留。两套业务 Compose、CI 夹具解析通过，契约 45 passed；零活动任务下完成单文件生产重建，全部目标服务健康且容器标签仅引用生产文件。重建后 metadata 22/23 succeeded，五个移除受控 Runner 的平台继续 anonymous 成功；唯一失败为既有 CQ-044 YouTube 会话过期。

## 037 AI 执行接入裁决（2026-09-17）

- CQ-AI-001，P3 / 重复风险：直接复制 DeepSeek 分析器会复制视频、剧本与改写提示词/限额逻辑。采用共享 ApiAnalyzer＋模型适配器组合；保留 CLI 工具调用边界。已实施，共享流程与 CLI 回归通过，真实模型待验收。
- CQ-AI-002，P2 / 行为缺陷：原 Profile 修改服务地址可保留旧 Key；本次新增 API 后必须绑定凭据目的地。现在地址/引擎变化要求显式新凭据，回归验证拒绝变更且原配置不变。已修复并通过确定性验收。
- CQ-AI-003，P2 / 键盘交互：AI 编辑器通过受控状态打开，缺少 DialogTrigger，Escape 后焦点落入 body。新增显式触发器焦点恢复，组件回归与生产构建浏览器复验通过。

### CQ-012：前端目录职责与冗余层

证据基线：10abe772。lib/hooks/services/types/utils 中 36 个源码文件均有生产引用，不能将文件数直接视为死代码；types/video.ts 重命名生成接口类型，utils/idempotency.ts 只转发 UUID，公共 Hooks 混放单业务状态流程。

最小修复：删除重复接口类型层和转发函数，合并同职责格式化函数，业务 Hooks 与展示逻辑就近放到组件目录，共享导入流程放 lib/upload。API 生成目录、Axios 封装、上传取消、认证和任务竞态逻辑保留。目录规范统一记录在 PROJECT.md。

验收：Biome、TypeScript、64 文件 / 300 项测试和 Next.js production build；纯目录与类型整理，不以本轮检查声明平台下载恢复或新生产部署。
