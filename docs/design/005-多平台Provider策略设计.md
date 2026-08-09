# 多平台 Provider 策略设计

## 目标

在不修改下载用例、格式选择、FFmpeg 校验和对象存储流程的前提下，统一接入主流公开视频平台，并让平台 URL 变化和请求差异集中在 Runner 内部。

## 模式组合

```text
输入 URL
  ↓
ProviderRegistry（Registry / Factory）
  ↓
ProviderProfile（Strategy） ── URL 规范化、固定请求参数、重试与出口策略
  ↓
MediaCommands（Template Method） ── inspect / download / probe / remux
  ↓
yt-dlp extractor → FFmpeg → ffprobe
```

- Strategy：`ProviderProfile` 描述一个平台族的域名别名、规范化函数和有限重试策略；Runner 可按稳定 Provider key 选择运维配置的受控出口。
- Registry / Factory：`ProviderRegistry` 使用标准化 hostname 选择策略，未知域名使用 Generic fallback。
- Template Method：`MediaCommands` 固定媒体处理生命周期，平台策略不能改变安全边界、输出限制或校验流程。
- Adapter：yt-dlp CLI 被 `MediaCommands` 隔离为受控子进程，平台 extractor 不直接进入 API 或领域层。

## 平台目录

当前登记并在镜像 yt-dlp extractor 清单中核验的平台：YouTube、Bilibili、抖音、TikTok、小红书、Vimeo、X/Twitter、Instagram、Facebook、Twitch、Reddit、Pinterest、微博、优酷、腾讯视频、Dailymotion、NicoNico。

抖音精选页 `modal_id` 与 `/share/video/{id}` 会先转换到标准视频地址，短链由 yt-dlp Generic extractor 在受控代理内跟随到标准地址。随 Runner 交付的可信抖音插件覆盖内置 extractor：它只用已校验的数字视频 ID 请求固定的 `www.iesdouyin.com/share/video/{id}/` 公开分享页、校验返回 ID 一致后复用 yt-dlp 元数据解析器。分享页缺失或受限时回退到官方 extractor 和稳定错误分类；系统不上传 Cookie、不生成平台签名，也不承诺无水印或原始母版。

小红书完整作品地址与 `xhslink.com/a|m` 短链使用受限浏览器指纹和有限重试。API 入口可从分享文案中提取恰好一个 HTTP(S) URL；多个 URL 仍拒绝。对新版省略 scheme 的小红书短链保留专用 `https://` 补全，其他无 scheme 输入不泛化。

## 约束

1. Provider Strategy 只能返回固定、审计过的参数，禁止透传用户提供的 yt-dlp 参数。
2. 所有平台仍使用相同的 URL 安全校验、egress proxy、时长/大小限制、FFmpeg remux 和 ffprobe 校验。
3. 平台目录是路由优化和可观测性元数据，不是成功保证；yt-dlp extractor 变化必须通过真实解析测试确认。
4. 新平台只需新增 Profile、域名测试和受控解析测试，不得在 HTTP 路由中新增平台分支。
5. Provider 独立出口只能指向无 URL 凭据的内部 HTTP(S) 代理；未配置时回退到统一 egress proxy，不能直连外网。
