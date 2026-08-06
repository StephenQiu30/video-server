import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from '@/app';

const jobId = '33333333-3333-4333-8333-333333333333';

describe('routes', () => {
  it('uses the browser path by default', () => {
    window.history.replaceState({}, '', '/');

    render(<App />);

    expect(
      screen.getByRole('heading', { name: '万能视频下载与智能分析' }),
    ).toBeInTheDocument();
  });

  it('renders the not-found page for unknown paths', () => {
    render(<App path="/missing" />);

    expect(screen.getByText('页面不存在')).toBeInTheDocument();
  });

  it('renders a download task route', () => {
    render(<App path={`/downloads/${jobId}`} />);

    expect(
      screen.getByRole('heading', { name: '下载任务' }),
    ).toBeInTheDocument();
  });
});
