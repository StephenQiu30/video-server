import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DownloadPage from '@/pages/Download';

vi.mock('@ant-design/pro-components', () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock('@umijs/max', () => ({
  useNavigate: () => vi.fn(),
}));

describe('DownloadPage', () => {
  it('does not render an empty result card before inspection starts', () => {
    const { container } = render(<DownloadPage />);

    expect(
      screen.getByRole('heading', { name: '万能视频下载器' }),
    ).toBeInTheDocument();
    expect(container.querySelector('.content-wrap')).not.toBeInTheDocument();
    expect(screen.queryByText('等待解析公开视频')).not.toBeInTheDocument();
  });
});
