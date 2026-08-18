import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import AdminAiProvidersPage from '@/app/admin/ai-providers/page';

vi.mock('@/components/admin/admin-ai-providers-view', () => ({
  AdminAiProvidersView: () => <p>AI Provider 管理内容</p>,
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

describe('administrator AI Provider route', () => {
  it('keeps AI Provider configuration behind the administrator guard', () => {
    const { container } = render(<AdminAiProvidersPage />);

    expect(screen.getByText('AI Provider 管理内容')).toBeInTheDocument();
    expect(container.querySelector('section')).toHaveAttribute(
      'data-require-admin',
      'true',
    );
    expect(container.querySelector('.inner-page')).toHaveClass('inner-page');
  });
});
