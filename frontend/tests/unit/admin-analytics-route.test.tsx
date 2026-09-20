import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminAnalyticsPage from '@/app/admin/analytics/page';

vi.mock('@/components/admin/admin-analytics-view', () => ({
  AdminAnalyticsView: () => null,
}));

vi.mock('@/components/auth/protected-route', () => ({
  ProtectedRoute: ({
    children,
    requireAdmin,
  }: {
    children: ReactNode;
    requireAdmin?: boolean;
  }) => <div data-require-admin={String(requireAdmin)}>{children}</div>,
}));

describe('administrator analytics route', () => {
  it('keeps analytics behind the administrator guard', () => {
    const { container } = render(<AdminAnalyticsPage />);

    expect(container.querySelector('div')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
  });
});
