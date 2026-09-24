import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EngineCatalogPanel } from '@/components/admin/engine-catalog-panel';
import { QueryProvider } from '@/components/layout/query-provider';

const runtime = vi.hoisted(() => ({ read: vi.fn() }));
vi.mock('@/api/admin', () => ({ getAdminEngineCatalog: runtime.read }));

function catalog(): API.EngineCatalogResponse {
  return {
    scope: 'anonymous_runner',
    engine_version: '2026.8.19',
    engine_commit: 'a'.repeat(40),
    expected_engine_commit: 'b'.repeat(40),
    pin_matches: false,
    bundled_plugins_sha256: 'c'.repeat(64),
    pot_provider_version: '1.3.2',
    manifest_id: 'd'.repeat(64),
    candidates: Array.from({ length: 25 }, (_, index) => ({
      key: `Candidate${index}`,
      name: `Example ${index}`,
      upstream_working: index !== 0,
    })),
  };
}

describe('installed engine candidates', () => {
  beforeEach(() => {
    runtime.read.mockReset();
  });

  it('loads only on demand, paginates candidates and exposes pin mismatch', async () => {
    runtime.read.mockResolvedValue(catalog());
    render(
      <QueryProvider>
        <EngineCatalogPanel />
      </QueryProvider>,
    );
    expect(runtime.read).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '读取引擎候选' }));
    const list = await screen.findByRole('list', { name: '引擎候选清单' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(10);
    expect(
      screen.getByText(/候选数量不代表可下载的平台数量/),
    ).toBeInTheDocument();
    expect(screen.getByText(/安装版本与固定依赖不一致/)).toBeInTheDocument();
    expect(screen.getByText(/上游标记失效/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('搜索提取器候选'), {
      target: { value: 'Candidate24' },
    });
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByText('Example 24')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('搜索提取器候选'), {
      target: { value: 'missing' },
    });
    expect(
      screen.getByRole('heading', { name: '没有匹配的提取器' }),
    ).toBeInTheDocument();
  });

  it('retains the prior snapshot with an explicit notice on refresh failure', async () => {
    runtime.read
      .mockResolvedValueOnce(catalog())
      .mockRejectedValue(new Error('暂时不可用'));
    render(
      <QueryProvider>
        <EngineCatalogPanel />
      </QueryProvider>,
    );
    fireEvent.click(screen.getByRole('button', { name: '读取引擎候选' }));
    await screen.findByRole('list', { name: '引擎候选清单' });
    fireEvent.click(screen.getByRole('button', { name: '刷新引擎候选' }));
    await screen.findByText('引擎候选刷新失败，保留上次读取结果');
    expect(
      screen.getByRole('list', { name: '引擎候选清单' }),
    ).toBeInTheDocument();
    await waitFor(() => expect(runtime.read).toHaveBeenCalledTimes(2));
  });
});
