# 019 用户设备 Edge Agent 与媒体制品导入验收

<!-- acceptance: pending -->

- 状态：Pending，当前仅完成调研与设计
- 日期：2026-08-12
- 对应设计：`docs/design/019-用户设备EdgeAgent与媒体制品导入设计.md`
- 对应需求/计划：`docs/prd/019-用户设备EdgeAgent与媒体制品导入需求.md`、`docs/plans/019-用户设备EdgeAgent与媒体制品导入计划.md`

> 范围调整（2026-08-27）：浏览器本地上传和通用 Artifact Import 由 023 验收；本验收只要求其本地 MP4 子门禁，不等待无关的剧本模型质量。Edge 只传输用户显式选择且已经合法取得的 clear 文件；平台会话、网络采集、签名生成、受保护媒体处理和平台 Adapter 已全部移出 019。

## 1. 验收边界

本验收分为 023 本地 MP4 子门禁、设备协议、视频号明文文件导入和受控来源声明四个独立门禁。某个阶段通过不自动批准后续阶段；任何来源标签的文件导入只证明传输/Artifact 能力，不能批准相应平台链接下载。

生产分析继续接收完整视频文件。固定抽帧、客户端声明或仅 metadata 成功不能替代服务端 Artifact 校验和完整视频 Agent/报告证明。

## 2. 023 前置门禁

- [ ] 023 的浏览器 MP4、quarantine、Import Worker、视频 verifier、Artifact 晋升和崩溃恢复子门禁有完整证据；不依赖剧本文档/模型质量等无关验收项。
- [ ] Edge 路径通过 architecture/contract test 复用 023 上传与验证端口，仓库不存在第二套 multipart、quarantine 或 MP4 verifier。
- [ ] 现有远程下载与本地浏览器上传回归通过；这些证据不计作任何平台 canary。

## 3. 设备身份与协议验收

- [ ] 配对必须由已登录用户创建十分钟一次性 challenge；使用后和过期后均不能重放。
- [ ] 每安装密钥独立生成，服务端只保存公钥和凭据哈希；安装包、fixture 和日志无通用私钥。
- [ ] method/path/body hash/timestamp/nonce 任一篡改均拒绝；跨 owner 访问返回 404。
- [ ] 设备撤销、最低版本、blocked version、Import Profile kill switch 和 lease/version 检查均生效。
- [ ] Edge Agent 只能访问设备 API 和单对象上传会话，不能获得 DB/MQ/AI/MinIO 通用凭据。
- [ ] manifest 拒绝额外字段和敏感字段；API、DB、outbox、RabbitMQ、MinIO metadata、日志、trace、WebSocket 与报告扫描均无平台 Secret。
- [ ] 设备离线、上传恢复、会话过期、并发完成、取消和永久失联最终状态稳定且可恢复查询。
- [ ] Agent 安装包签名、SHA-256、SBOM、NOTICE、逐文件来源和可重复构建记录完整。

## 4. 微信视频号明文文件导入验收

- [ ] Agent 只接受用户通过系统文件选择器显式选择的标准 MP4，不接受视频号 URL、微信进程、浏览器 profile、缓存目录或网络流量来源。
- [ ] 仓库和发行物没有元宝 Cookie、私有 finder/解析接口、公共 Worker、CA、代理、注入、拦截、`decodeKey`、受保护前缀转换或相关回退模块。
- [ ] 本地预检只计算大小、SHA-256、BMFF/保护标记和 ffprobe；服务端仍独立执行完整验证。
- [ ] manifest 只包含允许的权利声明、脱敏来源、Agent/协议版本和不可逆指纹；敏感字段与未知字段拒绝。
- [ ] 损坏、加密、哈希不一致、超限、设备撤销、上传过期和取消负例通过，无可读孤儿。
- [ ] 项目自有或明确授权 MP4 完成文件选择、上传、服务端复验、Artifact、Analysis、报告与 WebSocket E2E。
- [ ] 详情显示 `acquired_by=customer/用户设备导入`，不显示平台下载成功。
- [ ] 视频号文件导入不写 Provider canary；`wechat_channels` 链接下载继续为 `unsupported`。

## 5. 受控来源声明验收

- [ ] `declared_origin` 只接受版本化枚举，不接受平台 URL、作品 id、provider key 或任意 metadata；来源为空仍可导入。
- [ ] 视频号、红果和其他来源标签都不创建 Provider canary、不提升平台状态，详情明确显示“用户设备文件导入”。
- [ ] Edge Agent 无平台域名访问能力；App/浏览器会话、设备参数、客户端签名、短时媒体信息、保护信息、缓存和内容密钥字段/流量负例全部拒绝。
- [ ] 项目自有 clear MP4 覆盖各来源标签的选择、上传、Artifact、完整视频 Analysis、报告与 WebSocket E2E，证据只计入 Import Profile。
- [ ] 正式平台下载/导出连接器必须有独立四件套、合同/API/未加密输出和 canary，不能复用本验收结果。

## 6. API、UI 与运维验收

- [ ] 所有新公开操作有唯一稳定 operationId，创建资源返回 `201 + Location`，OpenAPI 生成前端类型无手工漂移。
- [ ] Provider API 能区分 Runner、verified import 与 official connector；Runner access mode 未增加设备值，设备导入不显示为运维会话或平台下载。
- [ ] 下载详情、历史和管理员统计准确区分 remote/browser/edge 来源。
- [ ] 桌面、1280px 和 390×844 覆盖配对、上传、设备离线、需升级、取消、失败恢复和成功分析，无横向溢出。
- [ ] 后端 Ruff、format、mypy、全量 pytest；前端 lint、format、test、build 全部通过。
- [ ] 空/已有 PostgreSQL 数据卷幂等 schema，开发/生产 Compose 配置和真实依赖健康通过。
- [ ] 指标/告警覆盖验证队列、quarantine 孤儿、multipart、Import Profile 回归、旧 Agent、哈希不一致和终态不一致。
- [ ] main 推送后的 GitHub Actions 全部通过。

## 7. 真实证据记录模板

每个 Import Profile 单独填写，禁止复用其他路径结果：

```text
import profile / execution_mode / access_partition:
authorized sample owner and rights basis:
agent version / commit / package sha256:
profile version / source commit / SBOM:
OS / client version:
file selection checked_at / duration / outcome:
import id / download id / artifact sha256 / ffprobe summary:
analysis job / run / report / MD / DOCX / WebSocket evidence:
negative cases:
secret traffic and log audit:
import canary rows / explicit approval / Provider API result:
CI run:
```

记录不得包含完整平台链接、Cookie、Token、设备标识、内容密钥、证书私钥、签名媒体 URL 或平台原始响应。

## 8. 当前结论

023 已实现本地 MP4 导入基础，但 019 的设备协议和签名设备文件导入尚未实施。本验收保持 `pending`；任何平台来源标签都不得被标记为平台链接下载支持，也不得执行文档归档。
