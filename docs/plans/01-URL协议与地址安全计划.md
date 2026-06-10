---
layer: Plan
doc_no: "01"
audience:
  - Dev
  - QA
feature_area: url-protocol-address-safety
purpose: "实现 PRD01 中的 URL 协议校验与地址安全规则。"
canonical_path: "docs/plans/01-URL协议与地址安全计划.md"
status: active
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/01-解析入口与URL安全.md"
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
outputs:
  - "URL 安全校验实现计划"
triggers:
  - "需要落地 URL 校验规则"
downstream:
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PLAN01 URL 协议与地址安全

## 1. 背景

PRD01 已经定义了接收边界，本计划负责把协议、主机和地址安全规则变成可测试实现。

## 2. 目标

1. 覆盖 `http/https`、非法协议、空链接和危险地址。
2. 保证 URL 进入队列前已完成安全校验。

## 3. 非目标

- 不做平台识别。
- 不做任务创建与执行。

## 4. 核心内容

1. 增加 URL 解析与校验单元测试。
2. 拒绝 `localhost`、回环、内网和保留地址。
3. 对错误输入返回稳定错误码。

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/01-解析入口与URL安全.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/plans/04-创建任务与状态查询计划.md`

## 6. 验收门禁

- 入口安全测试通过。
- API 不会把危险地址加入任务队列。

## 7. 风险与边界

过于激进的地址拦截可能误杀短链接和边缘合法地址。

## 8. 待确认问题

- 是否允许配置白名单域名。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN01 |
