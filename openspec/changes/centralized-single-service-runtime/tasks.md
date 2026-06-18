## 1. PRD 文档

- [ ] 1.1 创建 `docs/prd/10-中心化单服务运行时.md`
- [ ] 1.2 验证 PRD10 明确要求 Compose 中只有一个业务服务 `app`
- [ ] 1.3 验证 PRD10 明确要求代码层只有一个部署入口
- [ ] 1.4 验证 PRD10 明确消息队列必须保留但作为内部机制
- [ ] 1.5 验证 PRD10 明确 MinIO/S3 是唯一最终交付入口
- [ ] 1.6 验证 PRD10 明确端到端链路要求

## 2. Design 文档

- [ ] 2.1 创建 `docs/design/03-中心化单服务架构重评审.md`
- [ ] 2.2 验证 DESIGN03 覆盖单入口、单 Compose 服务、队列内部化设计
- [ ] 2.3 验证 DESIGN03 包含架构图和数据流
- [ ] 2.4 验证 DESIGN03 包含失败路径和回滚影响

## 3. Acceptance 文档

- [ ] 3.1 创建 `docs/acceptance/03-中心化单服务与MinIO交付验收标准.md`
- [ ] 3.2 验证 ACC03 包含端到端链路验收场景
- [ ] 3.3 验证 ACC03 包含本地路径隔离验收
- [ ] 3.4 验证 ACC03 包含 readiness 验收

## 4. 索引更新

- [ ] 4.1 更新 `docs/prd/README.md` 添加 PRD10 条目
- [ ] 4.2 更新 `docs/design/README.md` 添加 DESIGN03 条目
- [ ] 4.3 更新 `docs/acceptance/README.md` 添加 ACC03 条目
- [ ] 4.4 更新 `docs/README.md` 引用新文档路径

## 5. OpenSpec 变更

- [ ] 5.1 创建 `openspec/changes/centralized-single-service-runtime/proposal.md`
- [ ] 5.2 创建 `openspec/changes/centralized-single-service-runtime/specs/centralized-single-service-runtime.md`
- [ ] 5.3 创建 `openspec/changes/centralized-single-service-runtime/design.md`
- [ ] 5.4 创建 `openspec/changes/centralized-single-service-runtime/tasks.md`

## 6. 验证

- [ ] 6.1 运行 `bash scripts/validate-repository.sh`
- [ ] 6.2 运行 `git diff --check`
- [ ] 6.3 人工复核 PRD10、DESIGN03、ACC03 对单服务、MinIO 交付和本地路径隔离的描述一致
- [ ] 6.4 复核文档中不再把 API/Worker 表达为两个业务服务
