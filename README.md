# 万能视频下载器

这是一个合规、安全、可自部署的视频下载与内容整理工具。采用 FastAPI、RQ、yt-dlp 构建。

## 核心功能

- **📥 视频全能解析**: 支持 YouTube, Bilibili, TikTok 等主流平台多分辨率解析。
- **✨ AI 智能全家桶**: 自动生成视频深度总结报告与 Mermaid 思维导图（基于 DeepSeek V3）。
- **📊 实时状态同步**: 基于 SSE (Server-Sent Events) 的任务进度与 AI 处理实时推送。
- **📄 专业报告导出**: 支持将 AI 分析洞察结果一键导出为专业 PDF 文件。
- **🛡️ 隐私安全存储**: 文件物理存储在私有 MinIO / S3 中，链接定时失效。

## 启动方式

### 本机调试（推荐）

本机调试只启动项目进程，PostgreSQL、Redis、MinIO 由 `.env` 指向已有本机服务：

```bash
cp .env.example .env
npm run dev:install
npm start
```

如需调试异步下载 Worker：

```bash
npm run dev:worker
# 或同时启动 API + Worker
npm run dev:all
```

### Docker 部署

Docker 作为部署方式使用，会启动 API、Worker、PostgreSQL、Redis 和 MinIO：

```bash
cp .env.production.example .env.production
# 替换所有 CHANGE_ME、域名、密钥和密码
npm run docker:up
```

停止部署：

```bash
npm run docker:down
```

默认服务地址：
- API：`http://localhost:8000`
- MinIO 控制台：`http://localhost:19001`

前端仓库已独立拆分：

- 前端项目：`https://github.com/StephenQiu30/video-web`

## 本地开发指南

1. **环境配置**：
   复制并填写根目录的 `.env` 文件。
   ```bash
   cp .env.example .env
   ```

2. **运行后端**：
   ```bash
   npm start
   ```

3. **运行 Worker**：
   ```bash
   npm run dev:worker
   ```

4. **前端请使用独立仓库启动：**
   ```bash
   git clone https://github.com/StephenQiu30/video-web.git
   ```

## 重要边界

- 仅用于用户拥有版权或合法授权的内容。
- 不支持 DRM 规避、付费墙绕过。
- 下载文件默认保留 24 小时。
