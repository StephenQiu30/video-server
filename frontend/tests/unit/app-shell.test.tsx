import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AppShell, AuthField, AuthPageFrame } from '@/components/app-shell';
import { InputGroupInput } from '@/components/ui/input-group';

const runtime = vi.hoisted(() => ({
  loading: false,
  pathname: '/',
  replace: vi.fn(),
  user: undefined as
    | undefined
    | {
        created_at: string;
        email: string;
        id: string;
        role: 'admin' | 'user';
        updated_at: string;
        username: string;
      },
}));

vi.mock('@/components/auth-provider', () => ({
  useAuth: () => ({
    loading: runtime.loading,
    signOut: vi.fn(),
    user: runtime.user,
  }),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => runtime.pathname,
  useRouter: () => ({ refresh: vi.fn(), replace: runtime.replace }),
}));

describe('AppShell', () => {
  beforeEach(() => {
    runtime.loading = false;
    runtime.pathname = '/';
    runtime.replace.mockReset();
    runtime.user = undefined;
  });

  it('renders the accessible Next.js product navigation on application routes', () => {
    render(
      <AppShell>
        <div>页面内容</div>
      </AppShell>,
    );

    const banner = screen.getByRole('banner');
    expect(banner).toBeInTheDocument();
    expect(banner.firstElementChild).toHaveClass('content-shell');
    expect(banner.firstElementChild).toHaveClass('h-20');
    expect(banner.firstElementChild).not.toHaveClass('page-shell');
    const brandLink = screen.getByRole('link', { name: '帧取首页' });
    expect(brandLink).toHaveAttribute('href', '/');
    expect(brandLink).toHaveClass('text-[17px]');
    expect(brandLink.querySelector('img')).toHaveAttribute('src', '/logo.svg');
    expect(brandLink.querySelector('img')).toHaveAttribute('width', '32');
    const desktopNavigation = screen.getByRole('navigation', {
      name: '主要导航',
    });
    const desktopHomeLink = within(desktopNavigation).getByRole('link', {
      name: '首页',
    });
    expect(desktopHomeLink).toHaveAttribute('href', '/');
    expect(desktopHomeLink).toHaveAttribute('aria-current', 'page');
    const historyLink = screen.getByRole('link', { name: /下载记录/ });
    expect(historyLink).toHaveAttribute('href', '/history');
    expect(historyLink).toHaveClass('min-h-11', 'text-[15px]');
    expect(historyLink.className).not.toContain('translate-y-px');
    expect(historyLink).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: /剧本文档/ })).toHaveAttribute(
      'href',
      '/documents',
    );
    expect(screen.getByRole('link', { name: /平台状态/ })).toHaveAttribute(
      'href',
      '/providers',
    );
    expect(screen.getByRole('link', { name: /账户/ })).toHaveAttribute(
      'href',
      '/user/login?redirect=%2F',
    );
    expect(document.querySelector('[data-slot="header-account"]')).toHaveClass(
      'w-[88px]',
      'shrink-0',
    );
    expect(desktopNavigation).toHaveClass('hidden', 'lg:flex');
    expect(
      within(desktopNavigation)
        .getAllByRole('link')
        .slice(0, 4)
        .map((link) => link.textContent),
    ).toEqual(['首页', '下载记录', '剧本文档', '平台状态']);
    expect(screen.getByRole('link', { name: '跳到主要内容' })).toHaveAttribute(
      'href',
      '#main-content',
    );
    expect(screen.getByRole('main')).toHaveClass('content-shell', 'flex-1');
    expect(screen.getByRole('contentinfo')).toHaveTextContent('帧取');

    const mobileMenuTrigger = screen.getByRole('button', {
      name: '打开导航菜单',
    });
    expect(mobileMenuTrigger).toHaveClass('lg:hidden');
    fireEvent.click(mobileMenuTrigger);
    const mobileNavigation = screen.getByRole('navigation', {
      name: '移动导航',
    });
    expect(
      within(mobileNavigation).getByRole('link', { name: '首页' }),
    ).toHaveAttribute('aria-current', 'page');
    expect(
      within(mobileNavigation).getByRole('link', { name: '下载记录' }),
    ).not.toHaveAttribute('aria-current');
    expect(
      within(mobileNavigation).getByRole('link', { name: '剧本文档' }),
    ).toHaveAttribute('href', '/documents');
    expect(
      within(mobileNavigation).getByRole('link', { name: '平台状态' }),
    ).toHaveAttribute('href', '/providers');
  });

  it('reserves the desktop account slot while authentication is loading', () => {
    runtime.loading = true;
    const { container } = render(
      <AppShell>
        <div>正在加载</div>
      </AppShell>,
    );

    const accountSlot = container.querySelector('[data-slot="header-account"]');
    expect(accountSlot).toHaveClass('w-[88px]', 'shrink-0');
    expect(accountSlot?.querySelector('[data-slot="skeleton"]')).toHaveClass(
      'h-11',
      'w-[74px]',
    );
    expect(
      screen.queryByRole('link', { name: /账户/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '打开导航菜单' })).toBeDisabled();
  });

  it('keeps explicit desktop and mobile routes from history back to parsing', async () => {
    runtime.pathname = '/history';
    render(
      <AppShell>
        <div>历史页面</div>
      </AppShell>,
    );

    expect(screen.getByRole('link', { name: '帧取首页' })).toHaveAttribute(
      'href',
      '/',
    );
    const desktopNavigation = screen.getByRole('navigation', {
      name: '主要导航',
    });
    expect(
      within(desktopNavigation).getByRole('link', { name: '下载记录' }),
    ).toHaveAttribute('aria-current', 'page');

    fireEvent.click(screen.getByRole('button', { name: '打开导航菜单' }));
    const mobileNavigation = await screen.findByRole('navigation', {
      name: '移动导航',
    });
    const mobileParserLink = within(mobileNavigation).getByRole('link', {
      name: '首页',
    });
    expect(mobileParserLink).toHaveAttribute('href', '/');
    expect(mobileParserLink).not.toHaveAttribute('aria-current');
    expect(
      within(mobileNavigation).getByRole('link', { name: '下载记录' }),
    ).toHaveAttribute('aria-current', 'page');
    fireEvent.click(mobileParserLink);
    expect(
      screen.queryByRole('navigation', { name: '移动导航' }),
    ).not.toBeInTheDocument();
  });

  it('exposes download analytics to administrators on desktop and mobile', async () => {
    runtime.pathname = '/admin/analytics';
    runtime.user = {
      created_at: '2026-08-09T10:00:00Z',
      email: 'owner@example.com',
      id: 'owner-id',
      role: 'admin',
      updated_at: '2026-08-09T10:00:00Z',
      username: 'owner',
    };
    render(
      <AppShell>
        <div>下载分析页面</div>
      </AppShell>,
    );

    fireEvent.pointerDown(
      screen.getByRole('button', { name: '打开账户菜单' }),
      { button: 0, ctrlKey: false },
    );
    const desktopLink = await screen.findByRole('menuitem', {
      name: '下载分析',
    });
    expect(desktopLink).toHaveAttribute('href', '/admin/analytics');
    expect(desktopLink).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('menuitem', { name: '平台目录' })).toHaveAttribute(
      'href',
      '/admin/providers',
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() =>
      expect(
        screen.queryByRole('menuitem', { name: '下载分析' }),
      ).not.toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole('button', { name: '打开导航菜单' }));
    const mobileNavigation = await screen.findByRole('navigation', {
      name: '移动导航',
    });
    const mobileLink = within(mobileNavigation).getByRole('link', {
      name: '下载分析',
    });
    expect(mobileLink).toHaveAttribute('href', '/admin/analytics');
    expect(mobileLink).toHaveAttribute('aria-current', 'page');
    expect(
      within(mobileNavigation).getByRole('link', { name: '平台目录' }),
    ).toHaveAttribute('href', '/admin/providers');
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

  it('keeps the authentication heading and field semantics accessible', () => {
    const { container } = render(
      <AuthPageFrame
        description="登录后继续使用。"
        title="登录帧取"
        titleId="login-title"
      >
        <AuthField
          error="请输入邮箱地址"
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
    expect(
      screen.queryByRole('link', { name: '返回上一步' }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('邮箱地址')).toHaveAttribute(
      'aria-describedby',
      'email-error',
    );
    expect(screen.getByRole('alert')).toHaveTextContent('请输入邮箱地址');
    expect(
      container.querySelector('section[aria-labelledby="login-title"]'),
    ).toHaveClass('max-w-[440px]');
    expect(
      container.querySelector('section[aria-labelledby="login-title"]')
        ?.parentElement,
    ).toHaveClass('justify-center', 'lg:justify-start');
    expect(container.querySelector('[data-slot="card"]')).toBeNull();
  });
});
