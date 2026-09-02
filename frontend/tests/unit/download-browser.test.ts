import { describe, expect, it, vi } from 'vitest';

import { triggerBrowserDownload } from '@/services/download';

describe('browser download', () => {
  it('starts attachment downloads in the current tab without opening a blank tab', () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});

    triggerBrowserDownload(
      'https://objects.example/signed-video',
      '示例视频.mp4',
    );

    const anchor = click.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.href).toBe('https://objects.example/signed-video');
    expect(anchor.download).toBe('示例视频.mp4');
    expect(anchor.rel).toBe('noopener');
    expect(anchor.target).toBe('');
    expect(anchor.isConnected).toBe(false);
  });
});
