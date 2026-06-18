# centralized-single-service-runtime

## 1. 单服务运行时定义

### 1.1 单入口规则

1. 代码层 SHALL 只有一个部署入口，即中心化 runtime。
2. 中心化 runtime MUST 在同一个进程内同时启动 API server、队列消费者和下载执行器。
3. MUST NOT 保留 `apps/api/app/main.py` 和 `apps/worker/worker/main.py` 两个独立部署入口。

### 1.2 单 Compose 服务规则

1. Docker Compose 中 SHALL 只有一个业务服务 `app`。
2. `app` 服务 MUST 使用单个 Docker target 构建。
3. MUST NOT 保留 `api` 和 `worker` 两个独立 Compose 业务服务。
4. 基础设施服务（PostgreSQL、Redis、MinIO）保持独立，不受影响。

### 1.3 队列内部化规则

1. Redis/RQ MUST 保留为同一项目内部的消息队列机制。
2. 队列消费 MUST 在 `app` 服务内部运行，不作为独立服务暴露。
3. MUST NOT 因为单服务化而移除 Redis/RQ。
4. MUST NOT 因为单服务化而改为 API 同步执行长耗时下载。

## 2. MinIO/S3 交付边界

### 2.1 唯一交付入口

1. MinIO/S3 SHALL 是唯一最终产物存储和读取入口。
2. 所有用户可访问的视频下载链接 MUST 通过预签名 URL 从 MinIO/S3 获取。
3. MUST NOT 把本地临时目录路径暴露到 API 响应、数据库记录或分享链接中。

### 2.2 本地路径隔离

1. Worker 下载的临时文件 MUST 存放在容器内部临时目录。
2. 临时目录路径 MUST NOT 出现在 `/api/tasks` 响应中。
3. 临时目录路径 MUST NOT 出现在数据库 `tasks` 表中。
4. 临时目录路径 MUST NOT 出现在任何用户可访问的 URL 中。
5. 任务完成后，临时文件 SHOULD 被清理。

## 3. Readiness 规则

### 3.1 就绪检查覆盖范围

`GET /ready` MUST 检查以下全部组件：

1. PostgreSQL 数据库连接。
2. Redis 连接。
3. RQ 队列可达。
4. MinIO/S3 对象存储可达。
5. 媒体工具（ffmpeg/ffprobe）可用。
6. 下载工作目录可写。

### 3.2 存活检查

`GET /health` MUST 返回 `{"status":"ok","app":"<app_name>"}` 表示进程存活。

### 3.3 失败语义

1. 任一组件不可用时，`/ready` MUST 返回 HTTP 503。
2. 响应 MUST 逐项报告每个组件的状态。
3. 对缺失依赖（如 ffmpeg）MUST 给出可操作提示。

## 4. 端到端链路验证

### 4.1 必须完成的链路

分享视频链接 MUST 能完成以下全部步骤：

1. URL 解析（`/api/parse`）。
2. 任务创建（`/api/tasks`）。
3. 队列消费（RQ Worker 在 app 内部）。
4. 下载执行（yt-dlp + FFmpeg）。
5. 产物上传到 MinIO/S3。
6. 预签名链接生成和读取。

### 4.2 验证方式

1. 自动化：`bash scripts/validate-repository.sh`
2. 手动：复核 PRD10、DESIGN03、ACC03 对单服务、MinIO 交付和本地路径隔离的描述一致。
3. Agent Review：检查文档是否仍把 API/Worker 表达为两个业务服务，是否误把本地路径作为交付方式。

## 5. 禁止行为

1. MUST NOT 保留 API/Worker 两个业务部署入口。
2. MUST NOT 在 API/DB 中暴露本地临时路径。
3. MUST NOT 把本地工作目录写成用户交付方式。
4. MUST NOT 移除 Redis/RQ。
5. MUST NOT 让 API 同步执行长耗时下载。
6. MUST NOT 引入 Kubernetes 或多服务编排。
