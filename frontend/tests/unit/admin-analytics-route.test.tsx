import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminAnalyticsPage from '@/app/admin/analytics/page';

vi.mock('@/components/admin/admin-analytics-view', () => ({
  AdminAnalyticsView: () => <p>分析内容</p>,
}));

vi.mock('@/components/auth/protected-route', () => ({
  ProtectedRoute: ({
    children,
    requireAdmin,
  }: {
    children: ReactNode;
    requireAdmin?: boolean;
  }) => <section data-require-admin={String(requireAdmin)}>{children}</section>,
}));

describe('administrator analytics route', () => {
  it('keeps analytics behind the administrator guard', () => {
    const { container } = render(<AdminAnalyticsPage />);

    expect(screen.getByText('分析内容')).toBeInTheDocument();
    expect(container.querySelector('section')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
    expect(container.querySelector('.inner-page')).toHaveClass('inner-page');
  });
});
