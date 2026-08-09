import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import NotFound from '@/app/not-found';
import MissingDownload from '@/components/missing-download';

describe('empty route states', () => {
  it('gives the not-found page a semantic page title', () => {
    render(<NotFound />);

    expect(
      screen.getByRole('heading', { level: 1, name: '页面未找到' }),
    ).toBeInTheDocument();
    expect(screen.getByText('404')).toHaveClass('text-muted-foreground');
  });

  it('gives a missing download a semantic page title', () => {
    render(<MissingDownload />);

    expect(
      screen.getByRole('heading', { level: 1, name: '下载任务不存在' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回下载历史' })).toHaveAttribute(
      'href',
      '/history',
    );
  });
});
