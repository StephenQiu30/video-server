# Simplify Ant Pro Download UI

## Why

当前工作台仍是左右分栏布局，并且成功任务使用大面积绿色提示块，和“Ant Design Pro 原生蓝白、单列下载器入口”的目标不一致。M1 当前重点是本地自用下载闭环，前端应突出粘贴链接、解析、创建任务和下载结果，不应呈现复杂 SaaS 工作台视觉。

## What Changes

- 工作台改为单列居中下载器形态，不再使用左右分栏。
- 页面配色收敛到 Ant Design Pro 默认蓝白风格。
- 成功任务改为轻量信息展示，不再使用大块绿色面板。
- 合规页改为单列上下结构，避免主要页面出现左右布局。
- 不改后端 API、下载任务、Worker、存储和 B 站下载逻辑。

## Impact

- Affected specs: `web-download-workspace`
- Affected code: 前端工作台、合规页、全局样式和少量验收文档
