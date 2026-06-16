## Why

video-server 后端代码结构基本遵循 `routers → services → models` 三层模式，但缺少正式的架构治理规范。`services/` 层同时承担业务编排和数据库读写，错误码和常量分散在各模块，新增模块缺乏明确的层级归属和依赖方向约束。PRD08 已定义治理边界，需要通过 OpenSpec 将分层架构、shared 真相源和架构边界测试规范化，为后续改造提供可验证的治理基线。

## What Changes

- 新增 OpenSpec spec `architecture-boundaries`：定义 router/schema/service/domain/repository/infrastructure/worker-job 的职责边界和依赖方向约束
- 新增 OpenSpec spec `shared-constants`：定义 `packages/shared/` 作为错误码、状态枚举和跨模块常量的唯一真相源
- 创建 `apps/api/app/domain/`、`apps/api/app/repositories/`、`apps/api/app/infrastructure/` 分层目录骨架
- 创建 `packages/shared/video_downloader_shared/codes.py`、`platforms.py`、`dto.py` 真相源模块
- 创建架构边界测试和 shared 常量完整性测试
- 创建复杂度控制检查脚本
- 将 specs 推广到 `openspec/specs/` 作为当前事实层
- 更新 `scripts/validate-repository.sh` 添加新文件检查

## Capabilities

### New Capabilities

- `architecture-boundaries`: 后端分层架构职责边界和依赖方向约束规范
- `shared-constants`: 跨模块常量和枚举作为唯一真相源的规范

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- 受影响代码：`apps/api/app/`（新增 domain/repositories/infrastructure 目录）、`packages/shared/video_downloader_shared/`（新增 codes/platforms/dto 模块）
- 受影响测试：`apps/api/tests/test_architecture_boundaries.py`、`apps/api/tests/test_shared_constants.py`
- 受影响文档：`docs/prd/08-后端工程规范与架构治理.md`、`docs/plans/13-后端工程规范与架构治理计划.md`、`docs/prd/README.md`、`docs/plans/README.md`
- 受影响脚本：`scripts/validate-repository.sh`、`scripts/check_complexity.sh`
