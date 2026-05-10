# Design

## Overview

本变更只稳定 M1 本地单用户下载闭环，不恢复登录注册，也不扩大到生产 SaaS。核心设计是：任务完成后仍由 API 生成短期链接，但链接指向后端下载代理而不是 MinIO / S3 内部地址。

## Backend

- `download-link` 校验任务归属、状态和保留期后，生成带 `expires` 与 HMAC `signature` 的 API URL。
- `download` 校验签名、状态和保留期后，从私有对象存储读取对象并用附件响应流式返回。
- `events` 暴露已有 `task_events` 表，任务详情可以查看状态历史。
- `retry` 不复用旧任务 ID，而是复制原任务输入创建新任务，旧任务保留事件记录。
- 创建和查询任务时补偿超时的 queued / running 任务，避免长期占用并发额度。

## Frontend

前端继续使用 React + Umi + Ant Design Pro。页面收敛为 ProLayout、PageContainer、ProCard、ProForm、ProTable、Descriptions 和 Timeline 等原生工作台组件；下载按钮只调用后端签名 URL，不直接处理对象存储地址。

## Compliance

本变更不新增 Cookie 托管、DRM 规避、付费墙绕过、会员内容绕过或平台专用解析。公网访问、JWT、用户隔离、限流、配额和管理员能力仍属于 `production-saas-readiness`。
