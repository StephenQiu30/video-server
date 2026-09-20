import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminAiProvidersPage from '@/app/admin/ai-providers/page';

vi.mock('@/components/admin/admin-ai-providers-view', () => ({
  AdminAiProvidersView: () => null,
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

describe('administrator AI Provider route', () => {
  it('keeps AI Provider configuration behind the administrator guard', () => {
    const { container } = render(<AdminAiProvidersPage />);

    expect(container.querySelector('div')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
  });
});
