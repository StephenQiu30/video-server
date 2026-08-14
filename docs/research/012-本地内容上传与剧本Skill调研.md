# 012 本地内容上传与剧本 Skill 调研

- 日期：2026-08-14
- 状态：调研完成
- 关联设计：`docs/design/023-本地内容上传与剧本分析设计.md`

## 1. 调研目标

为现有“解析公开链接 → 下载视频 → 创建视觉分析”的产品增加两类入口：

1. 用户从浏览器上传自己有权处理的本地 MP4，并继续使用现有导演拉片、任务状态和报告能力。
2. 用户上传剧本文档，只提供剧本分析、结构审阅和中英文改写，不扩张为通用文档问答或任意写作助手。

同时评估 GitHub 上可复用的 Agent Skill、剧本格式解析与长文档改写方案，明确许可证、供应链和当前运行时兼容边界。

## 2. 当前系统结论

### 2.1 可直接复用

- `019` 已设计浏览器 MP4 直传、MinIO quarantine、Import Worker、Artifact 晋升和现有 Analysis API 复用，可作为本地视频上传的基础。
- `010/012/013/015` 已提供完整视频 Analysis Worker、严格结果校验、报告持久化、重试、RabbitMQ 和 WebSocket 能力。
- 当前项目已经依赖 `python-docx` 和 `markdown-it-py`，可以复用 DOCX 文本读取与 Markdown/DOCX 报告输出。
- 当前 Skill 目录已经使用 `SKILL.md`、稳定 `skill_id`、服务端清单和创建时指令快照，适合继续作为受控业务能力目录。

### 2.2 不能直接复用

- `download_jobs.inspection_id/format_id` 和 `artifacts.duration_ms` 当前均为视频下载语义，文档不能伪造 inspection、format 或正时长。
- Analysis 工作区固定为 `input/video.bin`，Prompt、工具和结果契约固定要求 FFmpeg、连续分镜、高光和视觉资产。
- 当前 Skill loader 要求 frontmatter 恰好包含 `name/display_name/description/default_prompt/order`，无法读取标准 Agent Skills 的可选 `license/metadata/compatibility`，也不支持 `references/`。
- 所有现有 Skill 共享同一视频结果 Schema；只增加剧本文字 Prompt 会导致模型输出和服务端验证契约冲突。

## 3. GitHub Skill 调研

### 3.1 Agent Skills 标准

[agentskills/agentskills](https://github.com/agentskills/agentskills) 定义了 `SKILL.md` 的标准目录结构、`name/description` 必需字段、`license/compatibility/metadata/allowed-tools` 可选字段，以及 `scripts/`、`references/`、`assets/` 的渐进加载方式。其代码为 Apache-2.0，文档为 CC-BY-4.0。

可采用：

- 标准名称和描述字段；
- 可选许可证与来源 metadata；
- `SKILL.md` 小而明确、详细规则放一层 `references/`；
- CI 中执行静态校验。

不可直接采用：

- `allowed-tools` 不能扩大本项目 Analysis Worker 的工具权限；
- 外部 Skill 的脚本不能自动执行；
- 标准只定义打包和发现，不替代本项目的输入类型、结果 Schema、任务幂等和安全边界。

### 3.2 DirectorSKILL

[wuwangzhang1216/DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL) 使用 MIT 许可证，提供脚本与潜台词拆解、beats、视觉命题、导演阐述、blocking、镜头计划和 QC 流程。

适合提炼到本项目的内容：

- 表层事件、戏剧问题、内外冲突、潜台词和情绪运动；
- 可拍摄、可验证的视觉命题；
- 场景和节拍必须服务叙事目标；
- 修改建议必须能落实到表演、场面调度、镜头或剪辑决策。

不采用导演风格模仿模块，不复制具体电影的镜头、对白、角色或情节表达，也不把完整十三步制作流程塞进一次剧本分析任务。

### 3.3 jwynia/agent-skills

[jwynia/agent-skills](https://github.com/jwynia/agent-skills) 提供多个适合剧本审阅的 Skill，具体 Skill frontmatter 标记 MIT：

- `story-analysis`：核心冲突、人物、环境、转折、场景功能、情绪结构和主题收束；
- `scene-sequencing`：Goal → Conflict → Disaster 与 Reaction → Dilemma → Decision；
- `dialogue`：文本、潜台词、语境、角色声线和多重功能；
- `character-arc`：角色欲望、错误信念、选择与变化轨迹。

这些内容适合作为评分维度和诊断清单。其 Deno 脚本、会话文件持久化、交互式提问流程和跨 Skill 自动编排不进入服务端运行时。

### 3.4 translate-book

[deusyu/translate-book](https://github.com/deusyu/translate-book) 使用 MIT 许可证，支持 PDF/DOCX/EPUB 转换、分块、源文件 SHA-256 指纹、manifest、术语表、相邻上下文、选择性重跑和合并校验。

可借鉴的可靠性机制：

- 规范化文本与原始字节分别计算指纹；
- 按场景而不是固定字符数切分剧本；
- 先建立人物名、地点、专有名词和称谓术语表；
- 每个改写块携带相邻场景只读上下文；
- 合并时验证场景 ID 一一对应、源哈希未漂移且没有遗漏；
- 重试只重放缺失或失效的场景块。

不采用其 Calibre/Pandoc 依赖、模型内部并行 subagent 和任意文件写入方式。项目由可信 Worker 编排受限 CLI 调用，仍保持并发、超时、输出和工作区硬上限。

## 4. 文档解析候选

| 格式 | 首期方案 | 结论 |
| --- | --- | --- |
| DOCX | 复用 `python-docx`，只读取正文段落和允许的表格文本 | 纳入首期 |
| PDF | 固定 BSD-3-Clause 的 [pypdf 6.16.0](https://pypi.org/project/pypdf/)，对应上游 commit `2b60c99973df8d7f959cd46658604d881be3de3a` | 只接收未加密、无附件/活动内容且可提取文字的 PDF；不做 OCR；按官方建议在提取前检查解压后的 content stream 大小 |
| TXT/Markdown | 严格 UTF-8/受控编码检测、统一换行 | 纳入首期 |
| Fountain | 文本格式，按场景标题、角色、对白和动作行解析 | 纳入首期 |
| FDX | XML 格式；[screenplay-tools](https://github.com/wildwinter/screenplay-tools) 提供 MIT 参考实现 | 延后到后续阶段，先完成安全 XML 和中英文 fixture 验证 |

PyMuPDF 的 AGPL/商业双许可与当前 MIT 项目分发目标不匹配，本期不选。扫描 PDF 的 OCR 会新增模型、语言包、资源和隐私边界，也不进入首期。

## 5. 方案比较

| 方案 | 优点 | 主要问题 | 结论 |
| --- | --- | --- | --- |
| 把文档伪装成下载 Artifact | API 改动少 | 伪造时长/格式，污染下载历史，视频 Schema 无法校验 | 否决 |
| 新建完整平行文档 AI 系统 | 边界独立 | 重复任务、队列、报告、重试和 Provider 能力 | 否决 |
| 视频复用下载 Artifact，文档独立聚合，Analysis 统一编排 | 复用成熟链路且保持领域准确 | 需要 Analysis 输入和结果成为受控联合类型 | 采用 |
| 运行时从 GitHub 安装 Skill | 选择更新快 | 不可复现、许可证与恶意指令风险、运行时漂移 | 否决 |
| 审查后 vendor Skill 并固定 commit | 可审计、可测试、可复现 | 需要维护来源和升级流程 | 采用 |

## 6. 最终决策

1. `023` 承接所有浏览器本地文件上传；`019` 收敛为设备配对、Edge Import 和平台 Adapter，并复用 `023` 的上传隔离基础设施。
2. 本地视频仍产生 `download_job(source_kind=browser_import)` 与现有视频 Artifact，原样进入视频拉片。
3. 剧本文档使用独立 `documents/document_import_attempts`，保存原文件与规范化文本，不进入下载任务和视频 Artifact。
4. `analysis_jobs` 使用受数据库约束的 `input_kind` 和二选一输入引用；视频与剧本共享任务生命周期、Provider、报告和重试，使用不同的工作区、工具和结果契约。
5. 首批剧本 Skill 为 `screenplay-analysis`、`screenplay-structure-review`、`screenplay-rewrite`；输出能力只覆盖剧本分析与中英文改写。
6. GitHub Skill 只能作为经许可证和内容审查的规则来源；仓库保存来源 URL、固定 commit、许可证和本地改写说明，不允许生产环境自动下载或执行第三方脚本。

## 7. 已知风险

- PDF 文本顺序和中文字体映射可能失真；必须在导入完成前展示提取预览或明确拒绝低质量结果。
- 整部剧本改写的输出远大于普通分析；必须按场景分块、校验覆盖率并对输出字节设置独立上限。
- 不同模型对 Fountain/剧本格式遵循程度不同；格式正确性必须由服务端解析器复核，不能只信任 structured output。
- Skill 的许可证允许复用不代表分析方法或示例文本可以不保留来源；NOTICE 和逐 Skill 来源记录必须进入发布门禁。
- 文档正文同样可能包含 Prompt Injection；剧本执行器不得获得网络、Shell、Home、仓库或其他任务读取权限。
