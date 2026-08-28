---
name: video-to-article
description: 把视频重组为适合微信公众号阅读和二次编辑的文章初稿，保留章节证据、核心观点与发布前事实说明。
license: MIT
metadata:
  video-server-display-name: 公众号文章
  video-server-default-prompt: 将视频重组为微信公众号文章初稿：确定读者问题与中心命题，采用移动端短段落和信息型小标题，并把时间证据集中留给编辑复核。
  video-server-order: "25"
  video-server-input-kinds: video
  video-server-output-contract: video-article
  video-server-references: references/wechat-editorial.md
---
# 视频整理为公众号文章

目标是产出一篇离开播放器也能顺畅阅读的公众号文章初稿，而不是逐句字幕、时间线摘要或视觉拉片表。文章必须先建立中心命题和读者问题，再按信息逻辑重组视频内容；服务端会把正文与编辑证据分开渲染为 Markdown。

## 写作流程

1. 完整观察视频，列出可见主题、案例、数字/画面文字、转折和证据限制。
2. 选择一个中心命题，并确定最适合素材的文章骨架；不要把所有观察塞进同一篇文章。
3. 先形成章节论证链，再写标题、导语、正文、核心观点和结语。章节按问题推进，不按视频时间顺序机械复述。
4. 每章至少绑定一条真实时间证据；证据写给编辑复核，不要把时码硬塞进正文。
5. 最后执行事实、重复、移动端可读性、标题承诺和结尾新增结论检查。

## 输出纪律

- 标题准确具体，不使用“震惊”“必看”“真相了”等无证据承诺；导语用 2–3 句提出问题、对象和中心命题。
- 正文采用 3–7 个信息型章节；每章内部是完整短段落，不用列表堆砌代替论证，不编造采访、对白或外部资料。
- `key_points` 是编辑摘要，不是正文重复；`limitations` 记录字幕/音频/身份/外部背景等事实缺口。
- 结语只收束全文，不突然说教、拔高或加入新的事实和行动号召。
- 最终字段中不放 Markdown、HTML、代码围栏或额外 JSON；排版由服务端报告完成。

文章骨架、段落规范、编辑证据与发布前检查见 `references/wechat-editorial.md`。最终只返回 `video-article` Schema。
