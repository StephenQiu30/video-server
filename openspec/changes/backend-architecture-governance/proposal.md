## Why

视频下载后端已积累 router、service、core、schemas、models、worker 等多层职责，但缺少显式的依赖边界约束和架构治理规范。随着下载能力扩展（更多平台、更多处理流程），职责可能继续堆积到 router 或任务脚本中，导致耦合加深、测试困难、新贡献者无法快速定位职责归属。

需要通过 OpenSpec 将后端分层边界、依赖方向、单一事实来源和文档门禁固化下来，让后端可以长期按软件工程范式演进。

## What Changes

- 创建 PRD08（后端工程规范与架构治理）定义产品边界
- 创建 PLAN13（后端工程规范与架构治理计划）定义执行计划
- 新增 OpenSpec spec `backend-layer-boundaries`：定义 router/service/repository/adapter/task 的职责边界和依赖方向
- 新增架构边界测试 `test_architecture_boundaries.py`：约束 router 不直接依赖外部下载 SDK
- 更新 `scripts/validate-repository.sh` 检查 PRD08/PLAN13 存在性
- 更新 `docs/README.md` 索引

## Capabilities

### New Capabilities

- `backend-layer-boundaries`: 后端分层架构边界规范，覆盖 router/service/repository/adapter/task 的职责定义、依赖方向约束、单一事实来源要求

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- 受影响文档：`docs/prd/08-后端工程规范与架构治理.md`、`docs/plans/13-后端工程规范与架构治理计划.md`、`docs/README.md`
- 受影响测试：`apps/api/tests/test_architecture_boundaries.py`（新增）
- 受影响脚本：`scripts/validate-repository.sh`
- 受影响规范：`openspec/specs/backend-layer-boundaries/spec.md`（新增）
