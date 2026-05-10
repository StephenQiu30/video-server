## Why

项目已经完成本地 MVP 主链路验证，具备注册登录、解析、任务创建、Worker 下载、MinIO 私有存储和前端工作台基础能力。现在目标从“本地可用的视频下载器 MVP”推进到“可小范围公网内测的 SaaS 平台”，需要单独固化上线级账号安全、免费配额、管理员兜底、部署、可观测性和合规验收范围。

本变更不替代 `bootstrap-mvp-foundation`。M1 仍负责本地 MVP 收尾；本变更只管理上线级 SaaS 补齐工作，避免把本地验收和生产化验收混在一起。

## What Changes

- 固化第一版上线形态为小范围内测 SaaS。
- 增加注册控制、用户免费配额、任务限流和管理员兜底能力。
- 增加单机 Docker Compose + Nginx/TLS 的上线部署基线。
- 增加生产环境变量、备份恢复、对象生命周期、日志和监控要求。
- 增加公网内测验收标准，覆盖 API、前端、下载、部署、安全和合规负向样例。
- 明确第一版不接入支付订阅、不上 K8s、不做平台专用解析、不托管 Cookie、不做 AI 摘要。

## Capabilities

### New Capabilities

- `saas-beta-access-control`：小范围内测注册控制、用户状态、免费配额和管理员兜底。
- `production-deployment-baseline`：单机 Compose、Nginx/TLS、生产环境变量、备份恢复和健康检查。
- `production-acceptance-gates`：公网内测上线前的 API、前端、下载、安全、合规和运维验收门禁。

### Modified Capabilities

- `video-download-tasks`：在既有下载任务基础上增加免费配额、限流、失败治理和管理员可见性要求。
- `object-storage-delivery`：在既有私有对象存储基础上增加生产保留期、生命周期清理和备份策略要求。

## Impact

- 前端：需要补齐内测注册提示、配额展示、任务失败状态、管理员入口和部署后的端到端验收。
- 后端：需要补齐注册控制、用户配额、管理员接口、限流、审计和生产安全检查。
- Worker：需要补齐任务超时、失败重试、清理机制和上线级运行观测。
- 基础设施：需要补齐单机 Compose、Nginx/TLS、备份恢复、日志监控和 CI/CD 门禁。
- 合规：继续遵守不规避 DRM、付费墙、会员限制、访问控制，不托管平台 Cookie 的边界。
