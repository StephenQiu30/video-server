# Tasks

## 1. Specs And Docs

- [x] 1.1 新增本机 B 站下载 OpenSpec 变更。
- [x] 1.2 更新 ADR，记录本机 Worker 读取 Chrome 登录态作为单用户例外。
- [x] 1.3 更新测试验收和执行计划文档。

## 2. Parse And Format Handling

- [x] 2.1 修复 B 站浮点时长和文件大小导致的响应校验失败。
- [x] 2.2 解析结果新增推荐下载格式，避免误选纯视频或纯音频。
- [x] 2.3 解析异常统一转中文错误，不再暴露 `Failed to fetch`。

## 3. Local Worker Cookie Support

- [x] 3.1 新增 `YTDLP_COOKIES_FROM_BROWSER` 配置。
- [x] 3.2 Worker 下载选项按配置读取 Chrome 登录态。
- [x] 3.3 Cookie 不可读时给出可诊断中文失败原因。

## 4. Startup And Smoke

- [x] 4.1 `npm start` 启动 Docker API/Web 和本机 Worker。
- [x] 4.2 `npm stop` 停止 Docker API/Web 和本机 Worker。
- [x] 4.3 修订合规 smoke，允许本机 Worker Cookie 例外但禁止 Cookie 入库/前端/API/日志。
- [x] 4.4 新增 B 站 Chrome live smoke。

## 5. Validation

- [x] 5.1 补充单元测试。
- [x] 5.2 运行 OpenSpec、后端测试、前端 lint/build、API smoke、合规 smoke。
- [x] 5.3 使用 B 站真实链接完成解析和下载验收，或记录可诊断阻塞原因。
