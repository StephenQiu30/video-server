export function triggerBrowserDownload(url: string, filename = ''): void {
  const frame = document.createElement('iframe');
  frame.dataset.framefetchDownload = '';
  frame.hidden = true;
  frame.title = filename ? `正在下载：${filename}` : '正在下载文件';
  frame.src = url;
  document.body.append(frame);
  window.setTimeout(() => frame.remove(), 60_000);
}
