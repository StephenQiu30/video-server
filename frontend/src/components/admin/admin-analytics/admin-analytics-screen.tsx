import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';

import { AnalyticsKpis } from '@/components/admin/admin-analytics/analytics-kpis';
import {
  AnalyticsEmpty,
  AnalyticsLoading,
} from '@/components/admin/admin-analytics/analytics-states';
import { DailyTrendChart } from '@/components/admin/admin-analytics/daily-trend-chart';
import { SourceBreakdown } from '@/components/admin/admin-analytics/source-breakdown';
import { SourcePerformance } from '@/components/admin/admin-analytics/source-performance';
import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import type {
  AdminDownloadAnalytics,
  AnalyticsPeriod,
} from '@/services/analytics';

import { formatDateRange } from './analytics-format';

type AdminAnalyticsScreenProps = {
  data: AdminDownloadAnalytics | null;
  days: AnalyticsPeriod;
  error: string | null;
  loading: boolean;
  onDaysChange: (days: AnalyticsPeriod) => void;
  onRetry: () => void;
};

const periods: AnalyticsPeriod[] = [7, 30, 90];

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
              <div className="flex w-full items-center gap-2 sm:w-auto">
                <ToggleGroup
                  aria-label="统计周期"
                  className="min-w-0 flex-1 gap-0 rounded-md bg-surface p-1 sm:flex-none"
                  onValueChange={(value) => {
                    if (value) onDaysChange(Number(value) as AnalyticsPeriod);
                  }}
                  role="group"
                  type="single"
                  value={String(days)}
                >
                  {periods.map((period) => (
                    <ToggleGroupItem
                      className="h-10 min-w-0 flex-1 px-3 opacity-100 data-[state=on]:bg-foreground data-[state=on]:text-background sm:min-w-14 sm:flex-none"
                      key={period}
                      value={String(period)}
                    >
                      {period} 天
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
                <Button
                  aria-label="刷新下载分析"
                  className="h-12 w-12 shrink-0 border-0 bg-surface px-0 sm:h-10 sm:w-auto sm:px-3"
                  disabled={loading}
                  onClick={onRetry}
                  type="button"
                  variant="outline"
                >
                  <ArrowClockwiseIcon aria-hidden />
                  <span className="hidden sm:inline">刷新</span>
                </Button>
              </div>
            </div>
          }
          description="集中查看下载规模、完成质量与视频源表现。"
          title="下载分析"
        />
      </div>

      {error ? (
        <Alert variant="destructive">
          <WarningCircleIcon aria-hidden />
          <AlertTitle>无法加载下载分析</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
            <span>{error}</span>
            <Button onClick={onRetry} type="button" variant="outline">
              重试
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {loading && !data ? <AnalyticsLoading /> : null}
      {!loading && !error && data?.summary.total === 0 ? (
        <AnalyticsEmpty />
      ) : null}
      {data && data.summary.total > 0 ? (
        <div className="space-y-12 sm:space-y-14">
          <AnalyticsKpis summary={data.summary} />
          <div className="grid items-start gap-12 xl:grid-cols-[minmax(0,2fr)_minmax(17rem,1fr)] xl:gap-10">
            <DailyTrendChart daily={data.daily} />
            <SourceBreakdown
              sources={data.sources}
              total={data.summary.total}
            />
          </div>
          <SourcePerformance sources={data.sources} />
        </div>
      ) : null}
    </section>
  );
}
