# video-server

个人可自部署的万能视频下载后端：解析公开视频链接、异步下载、产物归档与合规治理。前端 UI 见独立仓库 [video-web](https://github.com/StephenQiu30/video-web)。

## 简介

`video-server` 提供下载器的 API 与 Worker 运行时，面向「自己部署、自己使用」的场景设计。系统通过 FastAPI 接收请求，经 Redis Queue 调度 Worker，使用 `yt-dlp` 执行下载，并将视频与元数据写入 MinIO / S3 兼容存储，任务状态保存在 PostgreSQL。

**当前主线（MVP）**：URL 安全校验 → 平台识别 → 创建下载任务 → Worker 执行 → MinIO 归档 → 预签名交付。

**仓库内另含扩展能力**（AI 摘要、PDF 报告、SSE 进度等），详见代码与历史实现；新版 SDD 文档优先收束到下载主链路，见 [`docs/`](docs/README.md)。

## 功能概览

| 能力 | 说明 |
| --- | --- |
| 链接解析 | 支持 YouTube、Bilibili、TikTok 等主流平台，多分辨率与格式探测 |
| 异步下载 | RQ Worker 解耦执行，支持重试、取消与失败分类 |
| 产物归档 | MinIO 私有存储，预签名下载链接，默认定时过期 |
| 合规治理 | URL 安全校验、限流配额、日志脱敏、负向合规测试 |
| 自部署运行 | 本机调试与 Docker Compose 一键部署 |

## 技术栈

- **API**：FastAPI、Pydantic、OpenAPI
- **任务队列**：Redis、RQ
- **下载引擎**：yt-dlp
- **存储**：PostgreSQL（状态）、MinIO / S3（产物）
- **部署**：Docker Compose、Shell 脚本

## 快速开始

### 本机调试（推荐）

本机只启动 API / Worker；PostgreSQL、Redis、MinIO 由 `.env` 指向已有服务：

```bash
cp .env.example .env
npm run dev:install
npm start
```

启动 Worker：

```bash
npm run dev:worker
# 或 API + Worker 一起启动
npm run dev:all
```

检查依赖服务：

```bash
npm run check:local
```

### Docker 部署

启动 API、Worker、PostgreSQL、Redis、MinIO：

```bash
cp .env.production.example .env.production
# 替换 CHANGE_ME、域名、密钥和密码
npm run docker:up
```

停止：

```bash
npm run docker:down
```

默认地址：

- API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- MinIO 控制台：`http://localhost:19001`

## 项目结构

```text
video-server/
├── apps/
│   ├── api/          # FastAPI 服务（解析、任务、鉴权、管理）
│   └── worker/       # RQ Worker（下载、归档、失败处理）
├── packages/shared/  # API 与 Worker 共享领域模型
├── docs/             # PRD、设计、计划、验收、运维文档
├── openspec/         # SDD 规范层
├── scripts/          # 启动、校验、冒烟与运维脚本
├── CLAUDE.md         # Claude Agent 协作规范
└── WORKFLOW.md       # Symphony / Linear 编排配置
```

## 文档

| 目录 | 内容 |
| --- | --- |
| [`docs/prd/`](docs/prd/README.md) | 产品需求与 MVP 边界 |
| [`docs/design/`](docs/design/README.md) | 技术设计与架构 |
| [`docs/plans/`](docs/plans/README.md) | 执行计划与 Linear 映射 |
| [`docs/acceptance/`](docs/acceptance/README.md) | 验收方案与测试计划 |
| [`docs/operations/`](docs/operations/README.md) | 运行、部署与运维 |

入口说明见 [`docs/README.md`](docs/README.md)。

## 常用命令

```bash
npm test              # 仓库结构校验 + API 测试
npm start             # 本机启动 API
npm run dev:worker    # 本机启动 Worker
npm run docker:up     # Docker Compose 部署
npm run docker:config # 渲染并检查 Compose 配置
```

## 合规边界

- 仅用于用户拥有版权或合法授权的内容。
- 不支持 DRM 规避、付费墙绕过或盗版传播。
- 下载产物默认保留 24 小时（可通过配置调整）。

## 质量门禁

CI 在 `main` 分支执行测试、仓库结构校验、脚本语法检查、生产环境模板负向校验与 Docker Compose 配置渲染。

本地可复现：

```bash
npm test
set -e; cp .env.production.example .env.production; npm run docker:config; rm -f .env.production
```

`.env.production.example` 必须保留 `CHANGE_ME` 等占位符；直接用于生产会在校验阶段失败。

## 相关仓库

- 前端 UI：[StephenQiu30/video-web](https://github.com/StephenQiu30/video-web)
- Claude 规范模板：[StephenQiu30/stephen-cladue](https://github.com/StephenQiu30/stephen-cladue)

## License

见仓库根目录许可证文件（如已配置）。
