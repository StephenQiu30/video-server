# Shared Constants

## Purpose

定义 `packages/shared/video_downloader_shared/` 作为跨模块常量、枚举和 DTO 的唯一真相源。

## ADDED Requirements

### Requirement: Error codes defined in shared package
所有 `failure_code` 常量 SHALL 在 `packages/shared/video_downloader_shared/codes.py` 中统一定义，业务代码通过导入引用。

#### Scenario: New error code added to shared
- **WHEN** 开发者需要新增一个 `failure_code`
- **THEN** 先在 `codes.py` 中定义常量，再在业务代码中导入使用

#### Scenario: No hardcoded error code strings
- **WHEN** 检查 `apps/api/app/services/` 和 `apps/worker/worker/` 的代码
- **THEN** 不存在硬编码的 `failure_code` 字符串字面量

### Requirement: Task state enum in shared package
任务状态枚举 SHALL 在 `packages/shared/video_downloader_shared/states.py` 中定义，业务代码通过导入引用。

#### Scenario: State transitions use shared enum
- **WHEN** 业务代码需要引用任务状态
- **THEN** 导入 `TaskState` 枚举，不使用字符串字面量

### Requirement: Platform IDs defined in shared package
平台标识常量 SHALL 在 `packages/shared/video_downloader_shared/platforms.py` 中定义。

#### Scenario: Platform ID lookup uses shared constant
- **WHEN** 业务代码需要引用平台 ID
- **THEN** 导入 `platforms.py` 中的常量，不使用字符串字面量

### Requirement: Cross-module DTOs in shared package
跨 API 和 Worker 共享的数据传输对象 SHALL 在 `packages/shared/video_downloader_shared/dto.py` 中定义。

#### Scenario: DTO shared between API and Worker
- **WHEN** API 和 Worker 需要交换结构化数据
- **THEN** 使用 `dto.py` 中定义的 DTO 类，不各自定义兼容结构

### Requirement: Shared package has no app dependencies
`packages/shared/` SHALL 不依赖 `apps/api/` 或 `apps/worker/` 中的任何模块。

#### Scenario: No upward import from shared
- **WHEN** 检查 `packages/shared/` 的 import 语句
- **THEN** 不存在导入 `apps.api` 或 `apps.worker` 的语句
