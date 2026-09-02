import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('@/lib/home-transition-motion', () => ({
  createHomeResolutionTimeline: (_scope: HTMLElement, onComplete: () => void) =>
    onComplete(),
  createSessionRestoreTimeline: () => undefined,
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
    expect(screen.queryByText('公开首页')).not.toBeInTheDocument();
    expect(screen.queryByTestId('download-workspace')).not.toBeInTheDocument();
    const startup = screen.getByRole('status');
    expect(startup).toHaveAttribute('data-slot', 'empty');
    expect(startup).toHaveTextContent('正在确认当前会话');
    expect(startup.querySelector('[data-slot="progress"]')).not.toBeNull();
  });

  it('reveals only the workspace after an authenticated session is restored', async () => {
    runtime.loading = false;
    runtime.user = { username: 'video-user' };

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    expect(await screen.findByTestId('download-workspace')).toBeVisible();
    expect(screen.queryByText('公开首页')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
  });

  it('reveals only the public content for an anonymous visitor', async () => {
    runtime.loading = false;

    render(<HomeExperience publicHome={<h1>公开首页</h1>} />);

    expect(
      await screen.findByRole('heading', { name: '公开首页' }),
    ).toBeVisible();
    expect(screen.queryByTestId('download-workspace')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
  });
});
