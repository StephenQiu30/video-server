# 019 用户设备 Edge Agent 与媒体制品导入验收

<!-- acceptance: pending -->

- 状态：Pending，当前仅完成调研与设计
- 日期：2026-08-12
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`
- 对应需求/计划：`docs/prd/019-用户设备EdgeAgent与媒体制品导入需求.md`、`docs/plans/019-用户设备EdgeAgent与媒体制品导入计划.md`

## 1. 验收边界

本验收分为通用 Artifact Import、设备协议、微信视频号两个 Adapter 和红果 Android Adapter 五个独立门禁。某个阶段通过不自动批准后续阶段；浏览器上传通过不代表平台下载通过，视频号元宝路径通过不代表 Windows 回退通过，任何视频号证据也不能批准红果。

生产分析继续接收完整视频文件。固定抽帧、客户端声明或仅 metadata 成功不能替代服务端 Artifact 校验和完整视频 Agent/报告证明。

## 2. 通用 Artifact Import 验收

- [ ] `DownloadSourceKind`、按来源状态机和 SQL CHECK 正确；现有远程下载全量回归无行为变化。
- [ ] 浏览器单 MP4 直传不经过 API 内存/磁盘中转，且只能写确定 quarantine key。
- [ ] quarantine 对下载 API、Analysis Worker 和公开网络不可读，短 lifecycle 生效。
- [ ] 服务端重新计算大小/SHA-256，并验证 MP4、视频/音频轨、时长、codec 和配置上限。
- [ ] 假扩展名、损坏容器、无音频/无视频、外部引用、哈希不一致、超大小/时长均 fail closed。
- [ ] `artifact.import.verify.requested` 使用 transactional outbox、quorum queue、publisher confirm、manual ack、DLQ 和有界回灌。
- [ ] 重复 complete、重复消息、Worker 在复制前/后和 DB 提交前/后崩溃均只产生一个 Artifact。
- [ ] 成功、失败、取消、过期和中断 multipart 均清理 quarantine、part 与本地工作区；孤儿 reconciliation 有证据。
- [ ] 导入成功后复用现有 Analysis API，并完成完整视频 Agent、数据库报告、MinIO Markdown/DOCX 和 WebSocket E2E。
- [ ] 来源文案明确为原始媒体导入，未写入 Provider canary 或宣称平台下载。

## 3. 设备身份与协议验收

- [ ] 配对必须由已登录用户创建十分钟一次性 challenge；使用后和过期后均不能重放。
- [ ] 每安装密钥独立生成，服务端只保存公钥和凭据哈希；安装包、fixture 和日志无通用私钥。
- [ ] method/path/body hash/timestamp/nonce 任一篡改均拒绝；跨 owner 访问返回 404。
- [ ] 设备撤销、最低版本、blocked version、Adapter kill switch 和 lease/version 检查均生效。
- [ ] Edge Agent 只能访问设备 API 和单对象上传会话，不能获得 DB/MQ/AI/MinIO 通用凭据。
- [ ] manifest 拒绝额外字段和敏感字段；API、DB、outbox、RabbitMQ、MinIO metadata、日志、trace、WebSocket 与报告扫描均无平台 Secret。
- [ ] 设备离线、上传恢复、会话过期、并发完成、取消和永久失联最终状态稳定且可恢复查询。
- [ ] Agent 安装包签名、SHA-256、SBOM、NOTICE、逐文件来源和可重复构建记录完整。

## 4. 微信视频号元宝分享链接验收

- [ ] Adapter 只接受规定的 `weixin.qq.com/sph/<id>` 单视频入口，源和媒体请求均受固定域名/IP/重定向/超时边界约束。
- [ ] 元宝会话只存在用户本地安全存储；服务端流量和持久化未出现 Cookie、token、转换参数或签名媒体 URL。
- [ ] 可直接验证的 MP4 不执行额外转换；需转换样本、128 KiB 边界、错误参数不落盘和容器恢复真值测试通过。
- [ ] 分享链接过期、未登录、会话过期、无视频、错误作品、媒体域越界、转换失败、超限和取消负例通过。
- [ ] 项目自有或明确授权单视频完成本地 capture、上传、服务端复验、Artifact、Analysis、报告与 WebSocket E2E。
- [ ] `provider_canary_results` 记录 `access_mode=user_device`，并绑定 Agent/Adapter/客户端版本；证据不含用户设备 ID 或链接。
- [ ] 许可证/SBOM 证明未包含公共 Worker、Commons Clause 功能代码、来源不明 WASM/DLL、预置 Cookie/CA/私钥。
- [ ] 显式发布批准前 `wechat_channels` 保持 `unsupported`；批准后 Provider 页面准确显示用户设备要求。

## 5. Windows 微信客户端回退验收

- [ ] 只允许已批准 Windows/微信版本矩阵，其他版本 fail closed。
- [ ] 每安装动态 CA 与私钥，不存在仓库通用证书；安装前明确同意并可一键卸载。
- [ ] loopback 管理端口需要设备认证，局域网不可访问。
- [ ] 代理只覆盖批准进程/域名，媒体 CDN 默认直通；正常完成、取消、崩溃、重启和卸载均恢复原网络设置。
- [ ] 默认不持续监听，只捕获用户明确选择的单视频。
- [ ] 该 Adapter 使用独立 canary；元宝路径成功不会掩盖其版本回归。

## 6. 红果 Android 单集验收

- [ ] 使用用户控制的 Android/模拟器、固定红果 App/Agent 版本和明确授权单集。
- [ ] App 会话、设备参数、客户端签名、短时媒体信息、保护信息和内容密钥全部留在本地。
- [ ] manifest/流量/持久化只包含允许的单集元数据、来源指纹和最终 MP4 规格。
- [ ] 单集身份、时长、最终 MP4 和用户选择一致；一次任务不会静默扩展为整剧批量。
- [ ] App/Agent 版本不匹配、签名入口变化、会话过期、作品/分集错配、无权益、转换失败和超限负例通过。
- [ ] 项目自有或明确授权单集完成 capture、upload、Artifact、完整视频 Analysis、报告与 WebSocket E2E。
- [ ] 独立实现的算法真值、源码来源、SBOM 和许可证审计通过；无 LICENSE 参考仓库的代码/二进制未进入发行物。
- [ ] 显式发布批准前 `hongguo` 保持 `unsupported`；仅目录项或原始文件导入成功不改变状态。

## 7. API、UI 与运维验收

- [ ] 所有新公开操作有唯一稳定 operationId，创建资源返回 `201 + Location`，OpenAPI 生成前端类型无手工漂移。
- [ ] Provider API 能区分 extractor 与 Edge Adapter，`user_device` 文案不再显示为运维会话。
- [ ] 下载详情、历史和管理员统计准确区分 remote/browser/edge 来源。
- [ ] 桌面、1280px 和 390×844 覆盖配对、上传、设备离线、需升级、取消、失败恢复和成功分析，无横向溢出。
- [ ] 后端 Ruff、format、mypy、全量 pytest；前端 lint、format、test、build 全部通过。
- [ ] 空/已有 PostgreSQL 数据卷幂等 schema，开发/生产 Compose 配置和真实依赖健康通过。
- [ ] 指标/告警覆盖验证队列、quarantine 孤儿、multipart、Adapter 回归、旧 Agent、哈希不一致和终态不一致。
- [ ] main 推送后的 GitHub Actions 全部通过。

## 8. 真实证据记录模板

每个 Adapter 单独填写，禁止复用其他路径结果：

```text
provider / adapter / access_mode:
authorized sample owner and rights basis:
agent version / commit / package sha256:
adapter version / source commit / SBOM:
OS / client or app version:
capture checked_at / duration / outcome:
import id / download id / artifact sha256 / ffprobe summary:
analysis job / run / report / MD / DOCX / WebSocket evidence:
negative cases:
secret traffic and log audit:
canary rows / explicit approval / Provider API result:
CI run:
```

记录不得包含完整分享链接、Cookie、Token、设备标识、内容密钥、CA 私钥、签名媒体 URL 或平台原始响应。

## 9. 当前结论

当前只有开源调研、候选代码离线测试和视频号公开样例链路验证，服务端没有 Artifact Import、设备协议或平台 Adapter。本验收保持 `pending`，微信视频号和红果均不得标记为已支持，也不得执行文档归档。
