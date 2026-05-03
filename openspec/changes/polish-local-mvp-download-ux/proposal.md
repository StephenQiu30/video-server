# Polish Local MVP Download UX

## Why

M1 本地单用户闭环已经具备解析、任务、Worker、存储和下载代理，但用户在工作台输入无协议链接或触发下载时仍可能感知为“点击没反应”。同时工作台展示过多历史和 smoke 数据，影响单用户使用场景。

## What Changes

- URL 输入在前后端统一 trim，并为无协议域名链接自动补 `https://`。
- 解析、创建任务、下载、重试和取消动作提供 loading、disabled 和中文错误反馈。
- 下载按钮通过后端短期签名 URL 直接触发文件下载，不再依赖异步弹窗。
- 工作台仅展示新建下载和少量当前/最近关键任务，完整历史保留在任务历史页。
- 任务历史页支持分页、状态筛选、详情、下载、重试和取消。
- 任务列表和下载前轻量触发过期对象清理，保留历史记录但将文件入口标记为过期。

## Impact

- Affected specs: `project-runtime-foundation`, `video-download-tasks`
- Affected code: FastAPI parse/tasks API, worker cleanup reuse, React/Umi workspace/history/detail pages, smoke scripts, docs
