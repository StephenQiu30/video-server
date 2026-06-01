---
layer: Plan
doc_no: "005-01"
audience:
  - Dev
  - QA
feature_area: cookie-config
purpose: "定义自部署浏览器 Cookie 配置的实现计划，包括 Worker Cookie 选项处理、环境变量配置和测试验证。"
canonical_path: "docs/plans/005-01-自部署浏览器Cookie配置计划.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/005-自部署Cookie与合规治理.md"
  - "docs/06-运维合规/02-风险与合规边界.md"
  - "docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md"
outputs:
  - "Worker Cookie 选项处理逻辑"
  - "Cookie 配置相关单元测试"
triggers:
  - "自部署环境需要读取浏览器 Cookie 进行视频解析"
downstream:
  - "docs/acceptance/001-万能视频下载器MVP测试计划.md"
---

# PRD005-01 自部署浏览器 Cookie 配置计划

## 1. 背景

自部署场景下，部分平台的公开视频解析需要浏览器 Cookie（登录态、区域偏好等）才能正常获取视频信息。当前 Worker 的 yt-dlp 调用未支持 Cookie 参数。

本计划定义如何在 Worker 中添加 Cookie 配置支持，同时确保 Cookie 仅在自部署本机环境使用，不上传、不托管、不共享。

## 2. 目标

```gherkin
Given 自部署用户设置了 `YT_DLP_COOKIES_BROWSER=chrome`
When Worker 执行 yt-dlp 下载
Then yt-dlp 使用 `--cookies-from-browser chrome` 参数
And 下载完成后 Cookie 不持久化到任何存储
```

```gherkin
Given 自部署用户设置了 `YT_DLP_COOKIES_FILE=/path/to/cookies.txt`
When Worker 执行 yt-dlp 下载
Then yt-dlp 使用 `--cookies /path/to/cookies.txt` 参数
```

```gherkin
Given 未配置任何 Cookie 环境变量
When Worker 执行 yt-dlp 下载
Then yt-dlp 不使用 Cookie 参数，行为与当前一致
```

```gherkin
Given 配置了无效的浏览器类型 `YT_DLP_COOKIES_BROWSER=invalid_browser`
When Worker 启动配置校验
Then 系统记录警告日志并忽略该配置
```

## 3. 非目标

- 不提供 SaaS Cookie 上传、托管、共享或账号池。
- 不在 Web UI 中提供 Cookie 配置入口。
- 不持久化 Cookie 到数据库、对象存储或日志。
- 不支持自动 Cookie 刷新或轮换。
- 不绕过平台登录、验证码或访问控制。

## 4. 实现计划

### 4.1 环境变量配置

新增环境变量（写入 `.env.example` 和 `.env.production.example`）：

| 变量 | 说明 | 默认值 | 示例 |
| --- | --- | --- | --- |
| `YT_DLP_COOKIES_BROWSER` | 浏览器类型，用于 `--cookies-from-browser` | 空（不使用） | `chrome`, `firefox`, `edge` |
| `YT_DLP_COOKIES_FILE` | Netscape 格式 Cookie 文件路径 | 空（不使用） | `/home/user/cookies.txt` |

优先级：`YT_DLP_COOKIES_FILE` > `YT_DLP_COOKIES_BROWSER`。两者同时设置时使用文件方式。

### 4.2 Worker Cookie 选项处理

修改 `apps/worker/worker/download_runner.py`（或等效模块）：

```python
def build_cookie_args() -> list[str]:
    """构建 yt-dlp Cookie 参数。

    Cookie 仅在自部署本机环境使用：
    - 不上传到对象存储
    - 不写入数据库
    - 不记录到日志
    - 不持久化到任何共享存储
    """
    cookies_file = os.environ.get("YT_DLP_COOKIES_FILE", "").strip()
    cookies_browser = os.environ.get("YT_DLP_COOKIES_BROWSER", "").strip()

    if cookies_file:
        path = Path(cookies_file)
        if path.is_file():
            return ["--cookies", str(path)]
        else:
            logger.warning("Cookie 文件不存在，忽略: %s", cookies_file)
            return []

    if cookies_browser:
        supported = {"chrome", "firefox", "edge", "opera", "chromium", "brave", "vivaldi"}
        browser_lower = cookies_browser.lower()
        if browser_lower in supported:
            return ["--cookies-from-browser", browser_lower]
        else:
            logger.warning("不支持的浏览器类型，忽略: %s", cookies_browser)
            return []

    return []
```

### 4.3 配置校验

在 Worker 启动或配置检查脚本中增加 Cookie 配置校验：

- `YT_DLP_COOKIES_BROWSER` 值必须在支持列表中，否则记录警告。
- `YT_DLP_COOKIES_FILE` 路径必须存在且可读，否则记录警告。
- 校验结果仅写入日志，不影响 Worker 启动。

### 4.4 日志脱敏

确保以下场景的日志不包含 Cookie 内容：

- yt-dlp 命令行日志中不打印 `--cookies` 参数的文件内容。
- 下载失败日志不包含 Cookie 文件路径以外的 Cookie 信息。
- 已有日志脱敏规则（`docs/06-运维合规/02-风险与合规边界.md`）已覆盖 `cookie` 关键字。

### 4.5 测试计划

#### 单元测试

文件：`apps/api/tests/test_worker_reliability_modules.py`（或新建 `apps/worker/tests/test_cookie_config.py`）

| 测试场景 | 输入 | 预期输出 |
| --- | --- | --- |
| 支持浏览器类型 | `YT_DLP_COOKIES_BROWSER=chrome` | `["--cookies-from-browser", "chrome"]` |
| 支持浏览器类型（大小写） | `YT_DLP_COOKIES_BROWSER=Firefox` | `["--cookies-from-browser", "firefox"]` |
| 无效浏览器类型 | `YT_DLP_COOKIES_BROWSER=invalid` | `[]` + 警告日志 |
| 有效 Cookie 文件 | `YT_DLP_COOKIES_FILE=/path/to/cookies.txt`（文件存在） | `["--cookies", "/path/to/cookies.txt"]` |
| 无效 Cookie 文件路径 | `YT_DLP_COOKIES_FILE=/nonexistent` | `[]` + 警告日志 |
| 文件优先于浏览器 | 同时设置两个变量 | 使用文件方式 |
| 未配置 | 两个变量均为空 | `[]`，行为不变 |

#### 验证命令

```bash
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_worker_reliability_modules.py -q
```

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/005-自部署Cookie与合规治理.md`
2. `docs/06-运维合规/02-风险与合规边界.md`
3. `docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md`

### 5.2 输出文档

1. Cookie 选项处理代码变更
2. Cookie 配置单元测试

### 5.3 下游文档

1. `docs/acceptance/001-万能视频下载器MVP测试计划.md`

## 6. 验收门禁

- `build_cookie_args()` 函数覆盖支持浏览器、关闭值和无效值。
- Cookie 仅在自部署本机环境使用，SaaS 无 Cookie 上传/托管入口。
- Cookie 不写入日志、数据库或对象存储。
- 配置校验对无效值记录警告但不阻断 Worker。
- 单元测试全部通过。

## 7. 风险与边界

- `--cookies-from-browser` 依赖 yt-dlp 版本和操作系统，不同环境可能有兼容性差异。
- 部分浏览器（如 Chrome）在运行时锁定 Cookie 数据库，yt-dlp 可能需要关闭浏览器才能读取。
- Cookie 文件权限问题可能导致读取失败，需要明确错误提示。

## 8. 待确认问题

- 是否需要支持 Safari 浏览器（macOS 专属，yt-dlp 支持有限）。
- Cookie 配置是否需要支持运行时动态切换（当前计划为启动时读取环境变量）。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-01 | StephenQiu30 | 0.1.0 | 初始化自部署浏览器 Cookie 配置计划 |
