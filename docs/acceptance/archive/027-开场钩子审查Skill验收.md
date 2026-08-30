# 027 开场钩子审查 Skill 验收

<!-- acceptance: passed -->

- 状态：Passed
- 日期：2026-08-30

## 1. 目录与契约

- [x] `opening-hook-review` 按稳定顺序进入 video Skill 目录。
- [x] 输入类型仅为 `video`，结果契约为 `video-visual-analysis`。
- [x] 默认提示词、详细指令、reference 和 SHA-256 都由现有加载器生成。
- [x] Web 配置器通过现有目录 API 显示该 Skill，无专用前端硬编码。

## 2. 分析行为

- [x] 指令要求完整观察和连续覆盖全片时间轴。
- [x] 分别审查前 3 秒、5 秒和 15 秒，并处理不足 15 秒的视频。
- [x] 从可见主体、动作、构图、文字、状态变化和正文衔接给出证据化判断。
- [x] 不使用未获取的对白、语速、音乐、音效或情绪语气做结论。
- [x] 不把内部高光分数表述为留存、完播、点击或转化预测。
- [x] 修订建议引用真实 `shot.id`，不自动执行剪辑或生成。

## 3. 供应链与安全

- [x] 上游来源、commit、许可证和本地采用范围记入 `NOTICE.md`。
- [x] Skill 目录只包含 `SKILL.md` 和一层 Markdown references。
- [x] 不复制或执行上游脚本、资产、模板、MCP、网络调用或子 Agent 流程。
- [x] 不放宽现有文件、网络、Secret、Prompt Injection 和结果校验边界。

## 4. 验证

- [x] `quick_validate.py app/analysis_skills/opening-hook-review`（Skill is valid）
- [x] `uv run ruff check app tests`
- [x] `uv run mypy --strict app`
- [x] `uv run pytest -q tests/unit/infrastructure/test_analysis_skill_catalog.py tests/unit/infrastructure/ai_cli/test_prompt.py tests/unit/application/analysis/test_create_analysis.py`（37 passed）
- [x] 全量后端测试通过（1342 passed, 1 skipped）。
- [x] 受控授权视频的真实 Codex Provider canary 通过。

## 5. 真实 Provider canary 证据

| 项目 | 结果 |
| --- | --- |
| 日期 | 2026-08-30 |
| 输入 | 已存在的本地 dogfood 视频，18,947 ms，632,006 bytes，SHA-256 `f81b02555fa3e13cf319ad22b557413f39daccc261cca7e8476d660ceaf8ef48`；本轮没有抓取外部媒体 |
| 运行线路 | `local-codex` / `gpt-5.6-sol` / `codex-cli 0.149.1` |
| Skill 快照 | `opening-hook-review` / `62aeb2c92529f63355548021c83c70d69f405fd0e3655a69f163a8610e8ec5cf` |
| 结构验证 | Provider structured output 经 `parse_analysis_result` 和现有时间轴、场景分区、证据引用校验通过 |
| 开场行为 | 摘要分别给出 0–3、0–5、0–15 秒判断；全片连续覆盖 0–18,947 ms；受控 `hook-role`、`attention`、`pacing`、`payoff` 标签生效 |
| 证据边界 | 摘要、高光和制作建议只引用真实 `shot_001`；没有声称听到台词、音乐或音效，没有留存、完播、点击或转化预测 |
| 隔离与留存 | 使用生产同款受限视频观察工具和临时工作区；网络与 Home 访问禁用，原始模型响应和观察帧未持久化 |

样本本身是连续单镜头，因此本次真实 canary 验证了完整时长覆盖、短窗口诊断、
承诺兑现和证据边界；多 Cut 的确定性时间轴与引用规则继续由自动化测试覆盖。
