import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from '@/app';

const jobId = '33333333-3333-4333-8333-333333333333';

describe('routes', () => {
  it('uses the browser path by default', async () => {
    window.history.replaceState({}, '', '/');

    render(<App />);

    expect(
      await screen.findByRole(
        'heading',
        { name: '万能视频下载与智能分析' },
        { timeout: 5_000 },
      ),
    ).toBeInTheDocument();
  });

  it('renders the not-found page for unknown paths', async () => {
    render(<App path="/missing" />);

    expect(await screen.findByText('页面不存在')).toBeInTheDocument();
  });

  it('renders a download task route', async () => {
    render(<App path={`/downloads/${jobId}`} />);

    expect(
      await screen.findByRole('heading', { name: '下载任务' }),
    ).toBeInTheDocument();
  });
});
