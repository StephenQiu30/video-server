import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import NewDownloadPage from '@/app/downloads/new/page';

vi.mock('@/components/auth/protected-route', () => ({
  ProtectedRoute: ({ children }: { children: ReactNode }) => (
    <div data-testid="protected-route">{children}</div>
  ),
}));

vi.mock('@/components/intake/inspection-route', () => ({
  default: () => <div data-testid="inspection-route">解析结果</div>,
  InspectionSkeleton: () => <div>加载中</div>,
}));

vi.mock('@/components/layout/back-link', () => ({
  BackLink: ({ fallbackHref }: { fallbackHref: string }) => (
    <a href={fallbackHref}>返回上一步</a>
  ),
}));

describe('new download route', () => {
  it('dedicates the protected page to inspection results', () => {
    render(<NewDownloadPage />);

    expect(screen.getByTestId('protected-route')).toContainElement(
      screen.getByTestId('inspection-route'),
    );
    expect(screen.queryByTestId('download-workspace')).not.toBeInTheDocument();
  });
});
