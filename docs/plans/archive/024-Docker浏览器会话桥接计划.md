# 024 Docker 浏览器会话桥接计划

交付状态：已验收归档。

## 执行状态

- [x] 撤销 launchd Native Runner 与宿主机常驻运行目录。
- [x] 实现浏览器 Cookie 一次性导出、Provider 域过滤、登录态校验和权限收紧。
- [x] 配置 YouTube/TikTok Docker Operator Runner、固定出口与只读 Secret。
- [x] 修正 YouTube PO Provider 镜像 digest。
- [x] 为 TikTok 增加网页挑战兼容 extractor、稳定 device id 与受控 Operator 权益策略。
- [x] 为 Download Worker 增加 `runner_work` 共享卷并固定容器工作目录 `/work`。
- [x] 完成单元、类型、静态、Compose 合约与真实端到端验证。
- [x] 补齐设计、需求、运行手册与验收记录。

## 发布顺序

1. 在已登录浏览器导出两个平台的新版本 Cookie。
2. 设置路由、Secret 目录、版本、账号基线与 TikTok device id。
3. 启动 `youtube-operator`、`provider-operator` Profiles。
4. 先执行签名 metadata canary，再执行授权样本的最小格式下载。
5. 验证 Worker 共享卷、SHA-256、ffprobe 与 MinIO 交付后开放流量。

## 回滚

从 `RUNNER_OPERATOR_BASE_URLS` 移除目标 Provider，停止对应 Compose Profile，并恢复上一 Cookie version。不得回退到 launchd Runner、完整浏览器 Profile 挂载或远程调试端口。
