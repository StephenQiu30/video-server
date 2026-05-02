## Why

项目已完成市场调研、产品范围、合规边界和关键技术选型确认。现在需要进入 M1 MVP 骨架阶段，用 OpenSpec 固化首版实现边界，避免脚手架、账号、下载任务、存储和部署方案在实现时再次漂移。

## What Changes

- 初始化 React + Umi + Ant Design Pro 前端工程，作为下载工作台和账号入口。
- 初始化 FastAPI + Python 3.12 后端工程，提供鉴权、解析、任务和文件访问 API。
- 初始化 RQ Worker、Redis、PostgreSQL、MinIO / S3 兼容对象存储和 Docker Compose 本地运行环境。
- 实现 JWT 用户系统的 MVP 范围：允许注册、登录、当前用户查询和任务归属。
- 建立下载任务骨架：链接解析、任务创建、状态查询、取消、失败原因和对象存储输出。
- 建立成熟 MinIO 访问方式：私有 bucket、服务端生成短期预签名 URL、对象 key 按用户和任务隔离。
- 固化下载限制默认值：单任务最大 2GB、单任务最长 2 小时、全局并发 2、单用户并发 1、文件保留 24 小时。
- 首版不做 AI 摘要、支付会员、团队权限、Cookie 托管、平台专用解析和大规模批量抓取。

## Capabilities

### New Capabilities

- `project-runtime-foundation`: 项目脚手架、目录结构、Docker Compose、本地运行和基础配置。
- `user-auth`: JWT 用户注册、登录、当前用户和任务归属。
- `video-download-tasks`: 视频链接解析、格式选择、下载任务状态、取消、失败原因和限制策略。
- `object-storage-delivery`: MinIO / S3 私有存储、对象 key 规范、预签名 URL 和过期清理。

### Modified Capabilities

- 无。当前 OpenSpec specs 目录为空，本变更引入首批能力规范。

## Impact

- 前端：新增 `apps/web`，采用 React + Umi + Ant Design Pro。
- 后端：新增 `apps/api`，采用 FastAPI + Python 3.12。
- Worker：新增 `apps/worker`，采用 RQ + Redis 执行下载任务。
- 共享契约：新增 `packages/shared`，沉淀 API 类型、状态枚举和文档约定。
- 基础设施：新增 Docker Compose、PostgreSQL、Redis、MinIO、环境变量模板和本地启动文档。
- 合规：下载能力继续遵守“不规避 DRM、付费墙、会员限制、访问控制，不托管平台 Cookie”的边界。
