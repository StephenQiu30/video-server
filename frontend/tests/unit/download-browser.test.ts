import { afterEach, describe, expect, it, vi } from 'vitest';

import { triggerBrowserDownload } from '@/services/download';

describe('browser download', () => {
  afterEach(() => {
    vi.useRealTimers();
    document
      .querySelectorAll('[data-framefetch-download]')
      .forEach((element) => {
        element.remove();
      });
  });

  it('starts attachment downloads without navigating the current page', () => {
    vi.useFakeTimers();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});

    triggerBrowserDownload('about:blank#signed-video', '示例视频.mp4');

    expect(click).not.toHaveBeenCalled();
    const frame = document.querySelector<HTMLIFrameElement>(
      'iframe[data-framefetch-download]',
    );
    expect(frame).not.toBeNull();
    expect(frame?.src).toBe('about:blank#signed-video');
    expect(frame?.hidden).toBe(true);
    expect(frame?.title).toBe('正在下载：示例视频.mp4');
    expect(frame?.isConnected).toBe(true);

    vi.advanceTimersByTime(60_000);
    expect(frame?.isConnected).toBe(false);
  });
});
