import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminProvidersPage from '@/app/admin/providers/page';

vi.mock('@/components/admin/admin-provider-catalog-view', () => ({
  AdminProviderCatalogView: () => <p>平台目录内容</p>,
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

describe('administrator provider catalog route', () => {
  it('keeps catalog maintenance behind the administrator guard', () => {
    const { container } = render(<AdminProvidersPage />);

    expect(screen.getByText('平台目录内容')).toBeInTheDocument();
    expect(container.querySelector('section')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
    expect(container.querySelector('.inner-page')).toHaveClass('inner-page');
  });
});
