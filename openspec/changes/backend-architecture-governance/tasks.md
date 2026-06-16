## 1. OpenSpec Change Artifacts

- [x] 1.1 创建 `openspec/changes/backend-architecture-governance/proposal.md`
- [x] 1.2 创建 `openspec/changes/backend-architecture-governance/design.md`
- [x] 1.3 创建 `openspec/changes/backend-architecture-governance/specs/backend-layer-boundaries/spec.md`
- [x] 1.4 创建 `openspec/changes/backend-architecture-governance/tasks.md`

## 2. PRD 和 Plan 文档

- [x] 2.1 创建 `docs/prd/08-后端工程规范与架构治理.md`
- [x] 2.2 创建 `docs/plans/13-后端工程规范与架构治理计划.md`

## 3. 架构边界测试

- [x] 3.1 创建 `apps/api/tests/test_architecture_boundaries.py`
- [x] 3.2 验证 router 层不直接导入 yt_dlp
- [x] 3.3 验证 router 层不直接导入 minio
- [x] 3.4 验证 router 层不直接导入 SessionLocal
- [x] 3.5 验证 service 层不从 router 导入
- [x] 3.6 验证 core 层不从 service/router 导入

## 4. 文档和脚本更新

- [x] 4.1 更新 `docs/README.md` 添加 PRD08 和 PLAN13 索引
- [x] 4.2 更新 `scripts/validate-repository.sh` 检查 PRD08/PLAN13 存在性

## 5. 推广 Specs 到 Baseline

- [x] 5.1 推广 `backend-layer-boundaries` spec 到 `openspec/specs/backend-layer-boundaries/spec.md`

## 6. 验证

- [x] 6.1 运行 `pytest apps/api/tests/test_openapi_contract.py -v` (5 passed)
- [x] 6.2 运行 `pytest apps/api/tests/test_api_contract.py -v` (7 passed)
- [x] 6.3 运行 `pytest apps/api/tests/test_worker_jobs.py -v` (18 passed)
- [x] 6.4 运行 `pytest apps/api/tests/test_task_endpoints.py -v` (21 passed)
- [x] 6.5 运行 `pytest apps/api/tests/test_architecture_boundaries.py -v` (10 passed)
- [x] 6.6 运行 `bash scripts/validate-repository.sh` (passed)
