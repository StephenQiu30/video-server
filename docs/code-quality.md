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

## 3. 证据、最小修复与验收

### CQ-001：重试入口必须区分远程来源和本地上传

证据：[RetryDownload](../backend/app/services/downloads/retry_download.py)第 60–61 行明确拒绝非 `remote_provider`；[Web 详情](../frontend/src/components/downloads/download-state.tsx)第 52–54 行、[Web 列表](../frontend/src/components/downloads/download-history-list.tsx)第 92–94 行、[App 详情](../../video-app/lib/features/history/presentation/download_task_actions.dart)第 106 行附近与 [App 列表](../../video-app/lib/features/history/presentation/download_history_item.dart)第 116 行附近只按 status/fileAvailable 决定重试。响应已有 source_kind，无需新建接口。

影响：本地上传取消/失败或文件已不可取时，按钮会调用必然被拒绝的远程重试用例。服务器的拒绝是正确边界，不能为了按钮“能点”而删除。

最小修复：两端各收敛一份来源感知的操作判定，列表/详情共用；本地来源提供明确重新选择文件/重新导入入口，不静默创建远程任务。跨语言通过契约样例对齐，不建设共享运行时规则引擎。

验收：两端列表和详情都覆盖 `remote_provider/browser_import × failed/cancelled/succeeded-without-file`；本地不调用 retryDownload，远程保留原行为；保留服务端拒绝测试。

### CQ-002：视频上传复用已提交的幂等结果

证据：[media-import.ts](../frontend/src/services/media-import.ts)第 57–75 行创建资源后无条件申请 upload session；[document-import.ts](../frontend/src/services/document-import.ts)第 86–91 行会直接返回 verifying/ready 结果；[CreateUploadSession](../backend/app/services/imports/service.py)第 190 行拒绝非 uploading。既有 [媒体导入测试](../frontend/tests/unit/media-import.test.ts)第 172 行附近只为文档覆盖“完成响应丢失”。

影响：视频 complete 已被服务端接受、客户端没收到响应时，以同一 key 再次启动会取回 verifying/ready 资源，然后错误请求上传会话，无法从已有成功提交恢复。不是存储故障，也不应丢弃幂等键重复创建资源。

最小修复：视频流程消费真实资源状态；verifying/ready 直接返回，其他终态明确引导，只有 uploading 才申请分片会话。先补视频对应负例，不先重写整个上传器。

验收：verifying/ready 重放只发创建资源的幂等查询式请求，不重新 PUT 或 complete；uploading 正常上传；failed/cancelled/expired 不冒充成功。

实施结果：新增 verifying/ready 及 failed/cancelled/expired 五项用例，先失败后通过；视频服务按服务端状态恢复原资源，仅 uploading 继续传输。`media-import.test.ts` 全部 11 项通过，未改变后端或资源授权。浏览器完整上传验收仍待完成，不能以单测关闭端到端门禁。

### CQ-003：Web 任务更新必须按目标、操作代次和版本收敛

证据：[useDownloadJob](../frontend/src/hooks/useDownloadJob.ts)第 69–106 行包含独立 Socket/轮询 GET，Socket 回调 await 后没有失效检查；[useAnalysisJob](../frontend/src/hooks/useAnalysisJob.ts)第 74–114 行同样存在独立 GET，虽有 disposed 但都直接 setJob，没有响应 version 比较。两处 versionRef 用于订阅起点，不是写回保护；[task-socket](../frontend/src/lib/task-socket.ts)过滤事件版本也不能控制后续 HTTP 响应顺序。

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

证据：[download_history_repository.dart](../../video-app/lib/features/history/data/download_history_repository.dart)第 79–85 行每次 retry(jobId) 新建随机 key；两处 Widget 捕获错误后恢复按钮，再点击会重新调用该方法。相比之下，[Web 列表](../frontend/src/components/downloads/download-history-view.tsx)第 74–80 行和 [Web 详情 Hook](../frontend/src/hooks/useDownloadJob.ts)第 132 行附近在不确定失败后保留 key。服务端 RetryDownload 以原任务和 key 创建新任务，同源不同 key 可创建不同资源。

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

证据：[useMediaImport](../frontend/src/hooks/useMediaImport.ts)、[useDocumentImport](../frontend/src/hooks/useDocumentImport.ts)重复维护 ActiveRun、StableKey、取消与进度；[两类服务](../frontend/src/services/media-import.ts)和[文档服务](../frontend/src/services/document-import.ts)还复制 phase/observer 及传输编排。文档有失败取消和已完成恢复，视频有 declared_origin 与取消通知，不能简单互相替换。

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

- CQ-019 / P1 / 本机 YouTube 切片已修复：生产默认文件来源未准备，已安装按需助手没有被该拓扑使用，匿名线路被要求登录。增加仅 YouTube 的 Compose 来源覆盖、持久默认策略与精确启用说明，复用既有有界加密租约。68 项聚焦回归及原视频两次真实文件（含 Runner 强制重建）通过，不新增浏览器框架；其他平台仍分别验收。
- CQ-020 / P1 / 待专项修复与验收：既有 ProviderSessionStore 动态来源将 `credential_version_id` 固定为 browser，不能据此区分 Chrome 主体变化；文件来源有 keyed revision，动态来源没有相同保证。后续需明确同账号轮换与主体变更的识别，覆盖解析后换账号必须拒绝旧 context、Cookie 正常轮换和撤销测试；本轮不放松冻结校验，也不声称账号切换或迁移通过。
- CQ-021 / P1 / 修复验证中：Vimeo 固定样本声明独立音轨但 acodec 缺失，Runner 先接受可用纯视频，跳过音轨探测，导致 8101 生成静音制品并显示成功。复用有界探测补齐音轨，不猜编码、不缩短原时长；无法确认音轨时禁止静音误成功。需确定性回归及真实音视频交付后关闭，旧静音制品不改写。
- CQ-022 / P1 / 待修复：红果固定样本的 ffprobe 间歇返回 `Server returned 5XX Server Error reply`，稀疏格式补齐吞掉探测失败后对外归为 format_unavailable；重复 inspect/download 已确认可成功生成完整文件，不能据此永久认定格式不支持。需保留临时上游故障归因并评估原线路有界重试，覆盖部分格式可用、全部探测失败和总 deadline；不得以放宽计划匹配或换线路掩盖失败。

- CQ-018 / P2 / 已修复：链接入口向普通用户暴露访问策略、会话和证据细节，并为了选择器订阅平台状态、重复解析 URL 域名；配置了但未运行的受控端点还会成为隐含默认依赖。删除整套 Web 选择器及其状态/请求/提示函数，而非 CSS 隐藏；服务端复用现有部署默认和准入规则，允许公开访问的平台未覆盖时默认 public。入口、幂等、显式受控默认回归及 8101 真实页面验证通过，后端 1739/Web 283 项通过。此项仅关闭入口过度设计，不关闭实际 YouTube 下载故障或移动端收敛。

- CQ-015 / P1 / 已修复：Next.js standalone 构建期 rewrites 固定后端地址，候选 frontend 的运行时 BACKEND_ORIGIN 被忽略；用户新页面实际调用旧 API，策略缺失且失败被旧链路泛化。复用已有 proxy 运行时外部 rewrite，移除重复构建地址，不读取凭据或请求体。回归先 10 项失败后通过；Web 280 项、构建、lint/类型/格式及 23 项部署契约通过。真实已登录页面会话保持，策略出现，新 API 日志确认 GET/POST 到达。仅修复路由，不宣称该 YouTube 视频可下载。
- CQ-016 / P1 / 待修复：镜像构建提示依赖公告；`npm audit --omit=dev` 确认 next 16.3.0 的 critical 公告 GHSA-p293-qw3h-jr36、GHSA-2xp9-vwfh-vxw4，sharp 的 high 公告 GHSA-rgj7-g3m4-5g8c。当前候选为 Linux 且 images.unoptimized=true，不据此宣称已受攻击或所有利用条件成立；仍需独立升级受影响依赖、重新生成锁文件并完成全量/镜像/页面回归，再关闭该项。本次未更改依赖或自动执行 audit fix。
- CQ-017 / P1 / 已修复：真实 Chrome 发出的 `/api/auth/me/` 经代理到 FastAPI 后返回 307，Location 指向内部 `http://api:8111/api/auth/me`，导致外部浏览器无法恢复登录。代理将 API/health 尾斜杠规范化为后端真实路径，不重定向浏览器、不读取请求体或复制 Cookie。三个负例先失败后通过，全量 Web 283 项与构建通过；8101 的同一路径不再返回 Location，用户原 Chrome 会话无需重新登录即恢复。这里只证明登录和路由恢复，不证明 YouTube 文件交付。
