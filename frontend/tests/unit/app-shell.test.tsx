import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AppShell } from '@/components/app-shell';

const runtime = vi.hoisted(() => ({
  pathname: '/',
  replace: vi.fn(),
}));

vi.mock('@/components/auth-provider', () => ({
  useAuth: () => ({
    loading: false,
    signOut: vi.fn(),
    user: undefined,
  }),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => runtime.pathname,
  useRouter: () => ({ refresh: vi.fn(), replace: runtime.replace }),
}));

describe('AppShell', () => {
  beforeEach(() => {
    runtime.pathname = '/';
    runtime.replace.mockReset();
  });

  it('renders the accessible Next.js product navigation on application routes', () => {
    render(
      <AppShell>
        <main>页面内容</main>
      </AppShell>,
    );

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '帧取首页' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(screen.getByRole('link', { name: /下载历史/ })).toHaveAttribute(
      'href',
      '/history',
    );
    expect(screen.getByRole('link', { name: /账户/ })).toHaveAttribute(
      'href',
      '/user/login?redirect=%2F',
    );
    expect(screen.getByRole('link', { name: '跳到主要内容' })).toHaveAttribute(
      'href',
      '#main-content',
    );
  });

  it('removes the main navigation from authentication routes', () => {
    runtime.pathname = '/user/login';
    render(
      <AppShell>
        <main>登录页面</main>
      </AppShell>,
    );

    expect(screen.getByText('登录页面')).toBeInTheDocument();
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });
});
