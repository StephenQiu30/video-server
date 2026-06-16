# Tasks: 视频源可下载能力审计与中心化治理

## 任务列表

- [x] 1. 创建 OpenSpec change 结构
  - [x] 1.1 创建 `.openspec.yaml`
  - [x] 1.2 创建 `proposal.md`
  - [x] 1.3 创建 `specs/download-governance.md`
  - [x] 1.4 创建 `design.md`
  - [x] 1.5 创建 `tasks.md`

- [ ] 2. 治理旧适配器中心
  - [ ] 2.1 确认 `download_adapter.py` 中的逻辑已迁移到 `app.sources`
  - [ ] 2.2 在 `download_adapter.py` 中添加 deprecation 注释
  - [ ] 2.3 更新架构边界测试，断言旧中心不再作为独立中心

- [ ] 3. 建立支持矩阵文档
  - [ ] 3.1 创建 `docs/acceptance/02-视频源可下载支持矩阵.md`
  - [ ] 3.2 列出所有平台的支持状态
  - [ ] 3.3 为每个平台提供验证证据

- [ ] 4. 补充下载链路测试
  - [ ] 4.1 创建 `apps/api/tests/test_download_chain.py`
  - [ ] 4.2 为 B 站提供下载链路级测试
  - [ ] 4.3 为 YouTube 提供下载链路级测试
  - [ ] 4.4 为未知公网 fallback 提供测试
  - [ ] 4.5 为国内短视频平台提供受限/风控失败语义测试

- [ ] 5. 更新现有测试
  - [ ] 5.1 更新 `test_download_adapter.py` 测试引用
  - [ ] 5.2 更新 `test_platform_adapters.py` 测试引用
  - [ ] 5.3 更新 `test_architecture_boundaries.py` 增加边界约束

- [ ] 6. 验证与交付
  - [ ] 6.1 运行所有自动化测试
  - [ ] 6.2 运行架构边界测试
  - [ ] 6.3 人工审查支持矩阵
  - [ ] 6.4 准备 Agent Review 审查记录
