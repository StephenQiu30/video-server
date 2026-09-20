import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import NewDownloadPage from '@/app/downloads/new/page';

vi.mock('@/components/auth/protected-route', () => ({
  ProtectedRoute: ({ children }: { children: ReactNode }) => (
    <section data-testid="protected-route">{children}</section>
  ),
}));

vi.mock('@/components/intake/download-workspace', () => ({
  default: () => <div data-testid="download-workspace">新建下载工作区</div>,
}));

vi.mock('@/components/layout/back-link', () => ({
  BackLink: ({ fallbackHref }: { fallbackHref: string }) => (
    <a href={fallbackHref}>返回上一步</a>
  ),
}));

describe('new download route', () => {
  it('keeps the intake workspace on its own protected page', () => {
    render(<NewDownloadPage />);

    expect(screen.getByTestId('protected-route')).toContainElement(
      screen.getByTestId('download-workspace'),
    );
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/',
    );
  });
});
