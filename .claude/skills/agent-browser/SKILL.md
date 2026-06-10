---
name: agent-browser
description: Use for browser automation, localhost verification, page interaction, screenshots, and quick web checks with agent-browser.
---

# agent-browser

在需要打开网页、验证本地 dev server、点击页面元素、填写表单、抓取页面文本或截图时，优先使用 `agent-browser`。

## 适用场景

1. 本地服务启动后，需要验证页面是否可访问。
2. 需要对网页执行点击、输入、选择、提交等交互。
3. 需要截图、导出 PDF、抓取文本或确认页面标题、URL。
4. 需要对 localhost、127.0.0.1 或公开网页做快速可视化检查。

## 基本流程

1. 打开页面：`agent-browser open <url>`
2. 等待稳定：`agent-browser wait --load networkidle`
3. 获取交互元素：`agent-browser snapshot -i`
4. 使用 `@e1`、`@e2` 这类引用执行操作
5. 页面变化后重新 `snapshot -i`

## 常用命令

```bash
agent-browser open http://localhost:3000
agent-browser wait --load networkidle
agent-browser snapshot -i
agent-browser click @e1
agent-browser fill @e2 "hello"
agent-browser get title
agent-browser get url
agent-browser screenshot
agent-browser screenshot --full
agent-browser close
```

## 约束

1. 页面发生跳转、提交或动态刷新后，旧的 `@e*` 引用会失效，必须重新抓取。
2. 以最小必要动作为原则，不做与当前任务无关的浏览器操作。
3. 需要端到端证据时，可与 `harness-playwright-evidence` 配合使用；`agent-browser` 负责交互与快速验证。
