import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProviderRuntimePanel } from '@/components/admin/provider-runtime-panel';
import {
  httpRequests,
  mockHttpError,
  mockHttpResponses,
} from '../helpers/http';

describe('admin runtime diagnostics', () => {
  it('loads on demand and keeps reachability separate from download evidence', async () => {
    mockHttpResponses({
      snapshot_max_age_seconds: 30,
      items: [
        {
          provider_key: 'youtube',
          access_policy_id: 'operator_public',
          route_configured: true,
          context_available: true,
          profile_version: 'test',
          engine_commit: 'approved-engine',
          source_state: 'revision_observed',
          evidence_state: 'missing',
          last_media_verified_at: null,
          user_action: '请重新验证真实下载',
        },
      ],
    } satisfies API.ProviderRuntimeListResponse);
    render(<ProviderRuntimePanel />);
    expect(httpRequests()).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: '读取运行诊断' }));
    expect(
      await screen.findByText('已观测来源修订，授权有效性仍需验证'),
    ).toBeVisible();
    expect(screen.getByText(/无当前记录/)).toBeVisible();
    expect(screen.getByText('请重新验证真实下载')).toBeVisible();
    expect(httpRequests()[0].url).toBe('/api/admin/provider-runtime');
  });

  it('shows errors and retries to an explicit empty state', async () => {
    mockHttpError(new Error('offline'));
    mockHttpResponses({ items: [], snapshot_max_age_seconds: 30 });
    render(<ProviderRuntimePanel />);
    fireEvent.click(screen.getByRole('button', { name: '读取运行诊断' }));
    expect(await screen.findByRole('alert')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: '读取运行诊断' }));
    expect(await screen.findByText('暂无已开放平台。')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(httpRequests()).toHaveLength(2);
  });
});
