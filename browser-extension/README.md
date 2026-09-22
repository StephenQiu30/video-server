# FrameFetch 浏览器侧会话连接器

这个扩展是当前 Chrome 会话与本机 Access Agent 之间的桥。它使用 Chrome
官方 `cookies` API 读取平台白名单域，只把白名单 Cookie 交给本机 Native
Messaging 主机；Native Messaging 主机会在本机加密保存快照。Cookie 不经过
FrameFetch 前端页面，也不上传 API 或 Runner。

这是个人本机部署的可选账号授权适配器，不是公开解析或普通 Web 用户的前置依赖。共享宿主来源仅允许部署管理员显式授权；公开访客上下文由服务端单独维护。需要此适配器时按下列步骤安装：

1. 在 Chrome 打开 `chrome://extensions`，开启“开发者模式”，选择本目录
   `browser-extension` 加载未打包扩展。清单内置公开开发密钥，因此扩展 ID
   在不同机器保持稳定；安装后重新加载当前 FrameFetch 页面。
2. 先在 `backend` 目录安装按需 Access Agent（它负责消费加密快照，不直接读
   Chrome 数据库）：

   ```bash
   uv run python -m app.workers.runner.provider_cookie_agent install \
     --runtime-root "$HOME/Library/Caches/FrameFetch/provider-cookie-agent"
   ```

3. Agent 安装命令会同时注册与稳定扩展 ID 绑定的 Native Messaging 主机，
   不再复制扩展 ID 或单独执行桥接安装命令。

4. 管理员从产品内显式发起对应平台授权。API 先创建待处理事务，扩展携带该
   事务 ID 同步单个平台，Native Host 校验平台、来源和期限后才接收材料。
   粘贴链接、扩展启动或其他平台 Cookie 变化不会触发批量采集。快照接收成功
   不等于平台访问或媒体下载成功，仍需完成对应验证。

Native Messaging 主机只接受安装时绑定的扩展 ID 和固定本机 Runtime 目录。
跨机器安装不迁移第三方账号授权；新机器是否需要重新登录由平台策略决定。
不使用此可选账号路线时，用户无需安装扩展。

运行事务传递与并发同步回归：`node --test browser-extension/service-worker.test.mjs`。
