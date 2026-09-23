import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { HomeExperience } from '@/components/intake/home-experience';

const runtime = vi.hoisted(() => ({
  loading: true,
  user: undefined as { username: string } | undefined,
}));

vi.mock('@/components/auth/auth-provider', async (importOriginal) => ({
  ...(await importOriginal()),
  useAuth: () => runtime,
}));

vi.mock('@/components/intake/workspace-home', () => ({
  WorkspaceHome: () => <div data-testid="workspace-home">工作区</div>,
}));

describe('HomeExperience', () => {
  beforeEach(() => {
    runtime.loading = true;
    runtime.user = undefined;
  });

  it('does not mount either destination while the initial session is unresolved', () => {
    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    const experience = screen.getByRole('status').parentElement;
    expect(experience).toHaveAttribute('data-auth-pending', 'true');
    expect(experience).toHaveAttribute('data-home-phase', 'resolving');
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.queryByTestId('workspace-home')).not.toBeInTheDocument();
    const startup = screen.getByRole('status');
    expect(startup).toHaveTextContent('正在确认当前会话');
    expect(startup.querySelector('[data-slot="progress"]')).not.toBeNull();
  });

  it('shows server-selected public content during anonymous session discovery', () => {
    render(<HomeExperience initialPublic publicHome={<h1>公开首页</h1>} />);
    expect(screen.getByRole('heading')).toBeVisible();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByTestId('workspace-home')).not.toBeInTheDocument();
  });

  it('renders only the workspace after an authenticated session is restored', () => {
    runtime.loading = false;
    runtime.user = { username: 'video-user' };

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    expect(screen.getByTestId('workspace-home')).toBeVisible();
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(
      screen.getByTestId('workspace-home').closest('[data-home-view]'),
    ).toHaveAttribute('data-home-view', 'workspace');
  });

  it('renders only the public content for an anonymous visitor', () => {
    runtime.loading = false;

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    const publicHeading = screen.getByRole('heading', { level: 1 });
    expect(publicHeading).toBeVisible();
    expect(screen.queryByTestId('workspace-home')).not.toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(publicHeading.closest('[data-home-view]')).toHaveAttribute(
      'data-home-view',
      'public',
    );
  });
});
