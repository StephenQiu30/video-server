import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';

import { AnalyticsKpis } from '@/components/admin-analytics/analytics-kpis';
import {
  AnalyticsEmpty,
  AnalyticsLoading,
} from '@/components/admin-analytics/analytics-states';
import { DailyTrendChart } from '@/components/admin-analytics/daily-trend-chart';
import { SourceBreakdown } from '@/components/admin-analytics/source-breakdown';
import { SourcePerformance } from '@/components/admin-analytics/source-performance';
import { BackLink } from '@/components/back-link';
import { PageHeader } from '@/components/page-header';
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
    <section className="space-y-12">
      <div>
        <BackLink className="mb-7" fallbackHref="/account" />
        <PageHeader
          description="查看下载规模、完成情况与各视频源表现。"
          title="下载分析"
        />
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ToggleGroup
          aria-label="统计周期"
          className="w-fit gap-0 rounded-md bg-surface p-1"
          onValueChange={(value) => {
            if (value) onDaysChange(Number(value) as AnalyticsPeriod);
          }}
          role="group"
          type="single"
          value={String(days)}
        >
          {periods.map((period) => (
            <ToggleGroupItem
              className="h-11 min-w-16 px-4 opacity-100 data-[state=on]:bg-foreground data-[state=on]:text-background"
              key={period}
              value={String(period)}
            >
              {period} 天
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <div className="flex items-center justify-between gap-4 sm:justify-end">
          {data ? (
            <p className="font-mono text-xs text-muted-foreground">
              {formatDateRange(data.start, data.end)}
            </p>
          ) : null}
          <Button
            className="h-11 border-0 bg-surface px-4"
            disabled={loading}
            onClick={onRetry}
            type="button"
            variant="outline"
          >
            <ArrowClockwiseIcon aria-hidden />
            刷新
          </Button>
        </div>
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
        <div className="space-y-14 sm:space-y-16">
          <AnalyticsKpis summary={data.summary} />
          <DailyTrendChart daily={data.daily} />
          <SourceBreakdown sources={data.sources} total={data.summary.total} />
          <SourcePerformance sources={data.sources} />
        </div>
      ) : null}
    </section>
  );
}
