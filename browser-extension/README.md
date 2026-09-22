# FrameFetch 浏览器侧会话连接器

这个扩展是当前 Chrome 会话与本机 Access Agent 之间的桥。它使用 Chrome
官方 `cookies` API 读取平台白名单域，只把白名单 Cookie 交给本机 Native
Messaging 主机；Native Messaging 主机会在本机加密保存快照。Cookie 不经过
FrameFetch 前端页面，也不上传 API 或 Runner。

这是首次部署时的一次性安装步骤，不是每次下载步骤：

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

4. 保持当前 Chrome 登录平台；FrameFetch 只会在用户提交对应平台链接或主动
   续接授权时，静默刷新该平台的白名单会话，不会在扩展启动或其他平台 Cookie
   变化时批量采集。之后正常解析和下载不需要复制 Cookie、打开授权弹窗或重建
   容器。

Native Messaging 主机只接受安装时绑定的扩展 ID 和固定本机 Runtime 目录。
如果更换运行本项目的机器，只需在新机器完成一次同样的扩展/Native
Messaging 安装；平台登录本身仍由第三方的设备和出口策略决定。
