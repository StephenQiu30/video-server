import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HomeExperience } from '@/components/intake/home-experience';

const runtime = vi.hoisted(() => ({
  loading: true,
  user: undefined as { username: string } | undefined,
}));

vi.mock('@/components/auth/auth-provider', () => ({
  useAuth: () => runtime,
}));

vi.mock('@/components/intake/download-workspace', () => ({
  default: () => <div data-testid="download-workspace">工作区</div>,
}));

describe('HomeExperience', () => {
  beforeEach(() => {
    runtime.loading = true;
    runtime.user = undefined;
  });

  it('holds the server-rendered public content behind an auth gate while loading', () => {
    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    const experience = screen.getByRole('status').parentElement;
    expect(experience).toHaveAttribute('data-auth-pending', 'true');
    expect(screen.getByText('公开首页').parentElement).toHaveClass(
      'invisible',
    );
    expect(screen.getByRole('status')).toHaveTextContent('正在恢复登录状态');
  });

  it('reveals the workspace after an authenticated session is restored', () => {
    runtime.loading = false;
    runtime.user = { username: 'video-user' };

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    expect(screen.getByTestId('download-workspace')).toBeVisible();
    expect(screen.queryByText('公开首页')).not.toBeInTheDocument();
  });

  it('reveals the public content for an anonymous visitor', () => {
    runtime.loading = false;

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    expect(screen.getByRole('heading', { name: '公开首页' })).toBeVisible();
    expect(screen.queryByTestId('download-workspace')).not.toBeInTheDocument();
  });
});
