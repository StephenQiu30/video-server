# 027 开场钩子审查 Skill 计划

- 状态：Complete
- 日期：2026-08-30

## Phase 1：边界与供应链

- [x] 冻结开场 3/5/15 秒窗口、完整时间轴和视觉限制。
- [x] 记录上游来源、审阅 commit、许可证和本地重写范围。
- [x] 排除上游脚本、模板、资产、MCP、网络调用和自动生成流程。

## Phase 2：Skill 实现

- [x] 新增 `opening-hook-review/SKILL.md`。
- [x] 新增聚焦评估维度、字段映射和交付自检的 reference。
- [x] 使用已有 `video-visual-analysis` 契约并通过动态目录暴露给 Web。

## Phase 3：测试与验收

- [x] 更新目录顺序、reference 编译和生产边界测试。
- [x] 运行 Ruff、MyPy 和相关 Pytest。
- [x] 检查差异不包含用户现有改动、外部代码或未批准依赖。
- [x] 在受控授权样本上完成真实 Provider canary。
