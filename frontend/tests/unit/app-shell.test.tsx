import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AppShell, AuthField, AuthPageFrame } from '@/components/app-shell';
import { InputGroupInput } from '@/components/ui/input-group';

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
    expect(screen.getByRole('link', { name: '视频解析' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    const historyLink = screen.getByRole('link', { name: /下载历史/ });
    expect(historyLink).toHaveAttribute('href', '/history');
    expect(historyLink).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: /账户/ })).toHaveAttribute(
      'href',
      '/user/login?redirect=%2F',
    );
    expect(screen.getByRole('link', { name: '跳到主要内容' })).toHaveAttribute(
      'href',
      '#main-content',
    );

    fireEvent.click(screen.getByRole('button', { name: '打开导航菜单' }));
    const mobileNavigation = screen.getByRole('navigation', {
      name: '移动导航',
    });
    expect(
      within(mobileNavigation).getByRole('link', { name: '视频解析' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      within(mobileNavigation).getByRole('link', { name: '下载历史' }),
    ).not.toHaveAttribute('aria-current');
  });

  it('keeps explicit desktop and mobile routes from history back to parsing', async () => {
    runtime.pathname = '/history';
    render(
      <AppShell>
        <main>历史页面</main>
      </AppShell>,
    );

    const desktopNavigation = screen.getByRole('navigation', {
      name: '主要导航',
    });
    expect(
      within(desktopNavigation).getByRole('link', { name: '视频解析' }),
    ).toHaveAttribute('href', '/');
    expect(
      within(desktopNavigation).getByRole('link', { name: '下载历史' }),
    ).toHaveAttribute('aria-current', 'page');

    fireEvent.click(screen.getByRole('button', { name: '打开导航菜单' }));
    const mobileNavigation = await screen.findByRole('navigation', {
      name: '移动导航',
    });
    const mobileParserLink = within(mobileNavigation).getByRole('link', {
      name: '视频解析',
    });
    expect(mobileParserLink).toHaveAttribute('href', '/');
    expect(mobileParserLink).not.toHaveAttribute('aria-current');
    expect(
      within(mobileNavigation).getByRole('link', { name: '下载历史' }),
    ).toHaveAttribute('aria-current', 'page');
    fireEvent.click(mobileParserLink);
    expect(
      screen.queryByRole('navigation', { name: '移动导航' }),
    ).not.toBeInTheDocument();
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

  it('keeps the authentication card heading and field semantics accessible', () => {
    const { container } = render(
      <AuthPageFrame
        description="登录后继续使用。"
        title="登录帧取"
        titleId="login-title"
      >
        <AuthField
          error="请输入邮箱地址"
          icon={<span aria-hidden>@</span>}
          idPrefix="login"
          label="邮箱地址"
          name="email"
        >
          <InputGroupInput
            aria-describedby="email-error"
            aria-invalid
            id="login-email"
          />
        </AuthField>
      </AuthPageFrame>,
    );

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      '登录帧取',
    );
    expect(screen.getByLabelText('邮箱地址')).toHaveAttribute(
      'aria-describedby',
      'email-error',
    );
    expect(screen.getByRole('alert')).toHaveTextContent('请输入邮箱地址');
    expect(container.querySelector('[data-slot="card"]')).toHaveClass(
      'rounded-none',
      'bg-transparent',
      'ring-0',
    );
  });
});
