## 1. OpenSpec Change Artifacts

- [x] 1.1 创建 `openspec/changes/backend-engineering-governance/proposal.md`
- [x] 1.2 创建 `openspec/changes/backend-engineering-governance/design.md`
- [x] 1.3 创建 `openspec/changes/backend-engineering-governance/specs/architecture-boundaries/spec.md`
- [x] 1.4 创建 `openspec/changes/backend-engineering-governance/specs/shared-constants/spec.md`
- [x] 1.5 创建 `openspec/changes/backend-engineering-governance/tasks.md`

## 2. PRD 和 Plan 文档

- [x] 2.1 创建 `docs/prd/08-后端工程规范与架构治理.md`
- [x] 2.2 创建 `docs/plans/13-后端工程规范与架构治理计划.md`

## 3. Shared 真相源

- [ ] 3.1 创建 `packages/shared/video_downloader_shared/codes.py`，定义所有 `failure_code` 常量
- [ ] 3.2 创建 `packages/shared/video_downloader_shared/platforms.py`，定义平台 ID 常量
- [ ] 3.3 创建 `packages/shared/video_downloader_shared/dto.py`，定义跨模块 DTO
- [ ] 3.4 更新 `packages/shared/video_downloader_shared/__init__.py` 导出新模块

## 4. 分层目录骨架

- [ ] 4.1 创建 `apps/api/app/domain/__init__.py`，写入层级职责说明
- [ ] 4.2 创建 `apps/api/app/repositories/__init__.py`，写入层级职责说明
- [ ] 4.3 创建 `apps/api/app/infrastructure/__init__.py`，写入层级职责说明

## 5. 架构边界测试

- [ ] 5.1 创建 `apps/api/tests/test_architecture_boundaries.py`
  - 验证 router 不直接导入 ORM 模型
  - 验证 domain 不导入基础设施
  - 验证 repository 不含业务逻辑模式
- [ ] 5.2 创建 `apps/api/tests/test_shared_constants.py`
  - 验证 services 和 worker 中无硬编码错误码字符串

## 6. 复杂度控制

- [ ] 6.1 创建 `scripts/check_complexity.sh`，检查 Python 文件行数
- [ ] 6.2 将复杂度检查集成到 `npm test`

## 7. 文档与脚本更新

- [ ] 7.1 更新 `docs/prd/README.md` 添加 PRD08 条目
- [ ] 7.2 更新 `docs/plans/README.md` 添加 PLAN13 条目
- [ ] 7.3 更新 `scripts/validate-repository.sh` 添加新文件检查

## 8. 推广 Specs 到 Baseline

- [ ] 8.1 推广 `architecture-boundaries` spec 到 `openspec/specs/architecture-boundaries/spec.md`
- [ ] 8.2 推广 `shared-constants` spec 到 `openspec/specs/shared-constants/spec.md`

## 9. 验证

- [ ] 9.1 运行 `npm test` 确认所有测试通过
- [ ] 9.2 运行 `bash scripts/validate-repository.sh` 确认仓库结构检查通过
- [ ] 9.3 运行 `bash scripts/check_complexity.sh` 确认复杂度检查通过
