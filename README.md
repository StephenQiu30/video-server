# 万能视频下载器

这是一个合规、安全、可自部署的视频下载与内容整理工具。采用 FastAPI, RQ, Shadcn UI 和 DeepSeek AI 构建。

## 核心功能

- **📥 视频全能解析**: 支持 YouTube, Bilibili, TikTok 等主流平台多分辨率解析。
- **✨ AI 智能全家桶**: 自动生成视频深度总结报告与 Mermaid 思维导图（基于 DeepSeek V3）。
- **📊 实时状态同步**: 基于 SSE (Server-Sent Events) 的任务进度与 AI 处理实时推送。
- **📄 专业报告导出**: 支持将 AI 分析洞察结果一键导出为专业 PDF 文件。
- **🛡️ 隐私安全存储**: 文件物理存储在私有 MinIO / S3 中，链接定时失效。

## 一键启动

本项目通过 Docker Compose 实现快速部署：

- **全量独立堆栈**（推荐）：一键启动服务及基础设施（PostgreSQL, Redis, MinIO）。
  ```bash
  docker compose up -d --build
  ```

默认服务地址：
- 前端：`http://localhost:3000`
- API：`http://localhost:8000`
- MinIO 控制台：`http://localhost:9001`

## 本地开发指南

1. **环境配置**：
   复制并填写根目录的 `.env` 文件。
   ```bash
   cp .env.example .env
   ```

2. **运行后端**：
   ```bash
   cd apps/api && pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. **运行 Worker**：
   ```bash
   cd apps/worker && pip install -r requirements.txt
   python -m worker.main
   ```

4. **运行前端**：
   ```bash
   cd apps/web && npm install && npm run dev
   ```

## 重要边界

- 仅用于用户拥有版权或合法授权的内容。
- 不支持 DRM 规避、付费墙绕过。
- 下载文件默认保留 24 小时。
