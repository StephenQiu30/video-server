import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AdminAnalyticsView } from '@/components/admin-analytics-view';
import type { AdminDownloadAnalytics } from '@/services/analytics';

const runtime = vi.hoisted(() => ({
  getAdminDownloadAnalytics: vi.fn(),
}));

vi.mock('@/services/analytics', () => ({
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getAdminDownloadAnalytics: runtime.getAdminDownloadAnalytics,
}));

describe('administrator download analytics', () => {
  beforeEach(() => {
    runtime.getAdminDownloadAnalytics.mockReset();
  });

  it('renders KPI, accessible trend data and responsive source views', async () => {
    runtime.getAdminDownloadAnalytics.mockResolvedValue(analytics());
    render(<AdminAnalyticsView />);

    expect(
      await screen.findByRole('heading', { level: 1, name: '下载分析' }),
    ).toBeInTheDocument();
    expect(runtime.getAdminDownloadAnalytics).toHaveBeenCalledWith(30);
    expect(screen.getByText('下载总数').nextElementSibling).toHaveTextContent(
      '48',
    );
    expect(
      screen.getByText('成功率', { selector: 'dt' }).nextElementSibling,
    ).toHaveTextContent('75%');
    expect(screen.getByText('独立用户').nextElementSibling).toHaveTextContent(
      '12',
    );
    expect(screen.getByText('下载数据量').nextElementSibling).toHaveTextContent(
      '3 GB',
    );
    expect(screen.getByText(/平均视频时长/)).toHaveTextContent('2 分 5 秒');

    const responsiveCharts = screen.getAllByRole('img', {
      name: '每日下载任务折线趋势',
    });
    expect(responsiveCharts).toHaveLength(3);
    expect(
      responsiveCharts.map((chart) => chart.getAttribute('viewBox')),
    ).toEqual(['0 0 360 260', '0 0 640 270', '0 0 800 280']);
    const exactData = screen.getByRole('table', {
      name: '每日下载趋势精确数据',
    });
    expect(
      within(exactData).getByRole('row', { name: /2026-08-09 20 16 2 1/ }),
    ).toBeInTheDocument();

    expect(screen.getAllByRole('meter')).toHaveLength(2);
    expect(
      screen.getByRole('meter', { name: '抖音占全部下载的62.5%' }),
    ).toHaveAttribute('value', '62.5');
    expect(
      screen.getByRole('table', { name: '各视频源下载表现' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('rowheader', { name: /抖音 douyin/ }),
    ).toBeInTheDocument();
    expect(screen.getAllByText('抖音').length).toBeGreaterThan(1);
    expect(screen.getByRole('link', { name: '返回上一步' })).toHaveAttribute(
      'href',
      '/account',
    );
  });

  it('maps period changes and refresh to the analytics request', async () => {
    runtime.getAdminDownloadAnalytics.mockResolvedValue(analytics());
    render(<AdminAnalyticsView />);
    await screen.findByText('下载总数');

    const periodGroup = screen.getByRole('group', { name: '统计周期' });
    expect(
      within(periodGroup).getByRole('button', { name: '30 天' }),
    ).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(periodGroup).getByRole('button', { name: '7 天' }));
    await waitFor(() =>
      expect(runtime.getAdminDownloadAnalytics).toHaveBeenLastCalledWith(7),
    );
    expect(
      within(periodGroup).getByRole('button', { name: '7 天' }),
    ).toHaveAttribute('aria-pressed', 'true');

    await waitFor(() =>
      expect(screen.getByRole('button', { name: '刷新' })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole('button', { name: '刷新' }));
    await waitFor(() =>
      expect(runtime.getAdminDownloadAnalytics).toHaveBeenCalledTimes(3),
    );
  });

  it('covers loading, error retry and empty states', async () => {
    const first = deferred<AdminDownloadAnalytics>();
    runtime.getAdminDownloadAnalytics
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(
        analytics({
          daily: [],
          sources: [],
          summary: { ...analytics().summary, total: 0 },
        }),
      );
    render(<AdminAnalyticsView />);

    expect(
      screen.getByRole('status', { name: '正在加载下载分析' }),
    ).toBeInTheDocument();
    await act(async () => first.reject(new Error('统计服务暂不可用')));
    expect(await screen.findByText('统计服务暂不可用')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(
      await screen.findByText('当前周期还没有下载数据'),
    ).toBeInTheDocument();
  });
});

function analytics(
  overrides: Partial<AdminDownloadAnalytics> = {},
): AdminDownloadAnalytics {
  return {
    period_days: 30,
    start: '2026-07-12',
    end: '2026-08-10',
    summary: {
      total: 48,
      succeeded: 36,
      failed: 5,
      cancelled: 2,
      active: 5,
      unique_users: 12,
      downloaded_bytes: 3 * 1024 * 1024 * 1024,
      average_duration_seconds: 125,
      success_rate: 75,
    },
    daily: [
      {
        date: '2026-08-09',
        total: 20,
        succeeded: 16,
        failed: 2,
        cancelled: 1,
      },
      {
        date: '2026-08-10',
        total: 28,
        succeeded: 20,
        failed: 3,
        cancelled: 1,
      },
    ],
    sources: [
      {
        source_key: 'douyin',
        source_name: '抖音',
        total: 30,
        succeeded: 24,
        failed: 3,
        cancelled: 1,
        active: 2,
        unique_users: 9,
        downloaded_bytes: 2 * 1024 * 1024 * 1024,
        success_rate: 80,
      },
      {
        source_key: 'bilibili',
        source_name: '哔哩哔哩',
        total: 18,
        succeeded: 12,
        failed: 2,
        cancelled: 1,
        active: 3,
        unique_users: 6,
        downloaded_bytes: 1024 * 1024 * 1024,
        success_rate: 66.7,
      },
    ],
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, reject, resolve };
}
