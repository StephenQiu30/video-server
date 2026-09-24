import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { LinkDownloadForm } from '@/components/intake/link-download-form';

describe('LinkDownloadForm', () => {
  it('keeps the larger share-text field keyboard accessible', () => {
    const onInspect = vi.fn();

    render(
      <LinkDownloadForm
        busy={false}
        disabled={false}
        hasResult={false}
        invalid={false}
        onInspect={onInspect}
        onUrlChange={vi.fn()}
        url=""
      />,
    );

    const field = screen.getByRole('textbox', { name: '公开视频地址' });
    expect(field.tagName).toBe('TEXTAREA');

    fireEvent.click(screen.getByText('支持完整分享文案'));
    expect(field).toHaveFocus();

    fireEvent.keyDown(field, { key: 'Enter', shiftKey: true });
    expect(onInspect).not.toHaveBeenCalled();

    fireEvent.keyDown(field, { key: 'Enter' });
    expect(onInspect).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '解析媒体' }));
    expect(onInspect).toHaveBeenCalledTimes(2);
  });
});
