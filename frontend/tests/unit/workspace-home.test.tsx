import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { WorkspaceHome } from '@/components/intake/workspace-home';

describe('WorkspaceHome', () => {
  it('keeps task creation out of the authenticated home page', () => {
    render(<WorkspaceHome />);

    expect(screen.getByRole('link', { name: '新建下载' })).toHaveAttribute(
      'href',
      '/downloads/new',
    );
    expect(screen.getByRole('link', { name: '查看下载记录' })).toHaveAttribute(
      'href',
      '/history',
    );
    expect(
      screen.queryByRole('textbox', { name: '公开视频地址' }),
    ).not.toBeInTheDocument();
  });
});
