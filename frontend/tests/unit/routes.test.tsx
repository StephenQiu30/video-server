import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import DownloadRoute from '@/components/download-route';

describe('download route', () => {
  it('shows a useful empty state when jobId is missing', () => {
    render(<DownloadRoute />);
    expect(
      screen.getByRole('heading', { name: '下载任务不存在' }),
    ).toBeInTheDocument();
  });
});
