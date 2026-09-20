import { ArrowClockwiseIcon } from '@phosphor-icons/react';

import { AnalyticsKpis } from '@/components/admin/admin-analytics/analytics-kpis';
import { AnalyticsLoading } from '@/components/admin/admin-analytics/analytics-states';
import { CompletionRateChart } from '@/components/admin/admin-analytics/completion-rate-chart';
import { DailyTrendChart } from '@/components/admin/admin-analytics/daily-trend-chart';
import { SourceBreakdown } from '@/components/admin/admin-analytics/source-breakdown';
import { SourcePerformance } from '@/components/admin/admin-analytics/source-performance';
import { StatusDistributionChart } from '@/components/admin/admin-analytics/status-distribution-chart';
import { BackLink } from '@/components/layout/back-link';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { Button } from '@/components/ui/button';

import { formatDateRange } from './analytics-format';

type AdminAnalyticsScreenProps = {
  data: API.DownloadAnalyticsResponse | null;
  days: 7 | 30 | 90;
  error: string | null;
  loading: boolean;
  onDaysChange: (days: 7 | 30 | 90) => void;
  onRetry: () => void;
};

export function AdminAnalyticsScreen({
  data,
  days,
  error,
  loading,
  onDaysChange,
  onRetry,
}: AdminAnalyticsScreenProps) {
  return (
    <section aria-busy={loading} className="space-y-10 sm:space-y-12">
      <div>
        <BackLink className="mb-4" fallbackHref="/account" />
        <PageHeader
          action={
            <div className="flex flex-col gap-2 sm:items-end">
              {data ? (
                <p className="text-xs text-muted-foreground tabular-nums">
                  {formatDateRange(data.start, data.end)}
                </p>
              ) : null}
              <Button
                aria-label="刷新下载分析"
                className="h-12 w-12 shrink-0 bg-muted px-0 sm:h-10 sm:w-auto sm:px-3"
                disabled={loading}
                onClick={onRetry}
                type="button"
                variant="outline"
              >
                <ArrowClockwiseIcon aria-hidden />
                <span className="hidden sm:inline">刷新</span>
              </Button>
            </div>
          }
          description="集中查看下载规模、完成质量与视频源表现。"
          title="下载分析"
        />
      </div>

      {error ? (
        <PageErrorNotice
          message={error}
          onRetry={onRetry}
          title="无法加载下载分析"
        />
      ) : null}

      {loading && !data ? <AnalyticsLoading /> : null}
      {data ? (
        <DailyTrendChart
          daily={data.daily}
          days={days}
          onDaysChange={onDaysChange}
        />
      ) : null}
      {data && data.summary.total > 0 ? (
        <div className="space-y-12 sm:space-y-14">
          <AnalyticsKpis summary={data.summary} />
          <div className="grid gap-10 lg:grid-cols-3 lg:gap-12">
            <div>
              <StatusDistributionChart summary={data.summary} />
            </div>
            <div>
              <CompletionRateChart daily={data.daily} />
            </div>
            <div>
              <SourceBreakdown
                sources={data.sources}
                total={data.summary.total}
              />
            </div>
          </div>
          <SourcePerformance sources={data.sources} />
        </div>
      ) : null}
    </section>
  );
}
