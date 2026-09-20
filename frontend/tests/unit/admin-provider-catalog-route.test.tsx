import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminProvidersPage from '@/app/admin/providers/page';

vi.mock('@/components/admin/admin-provider-catalog-view', () => ({
  AdminProviderCatalogView: () => null,
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

describe('administrator provider catalog route', () => {
  it('keeps catalog maintenance behind the administrator guard', () => {
    const { container } = render(<AdminProvidersPage />);

    expect(container.querySelector('div')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
  });
});
