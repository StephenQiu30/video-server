import { ArrowClockwiseIcon } from '@phosphor-icons/react';

import { AnalyticsKpis } from '@/components/admin/admin-analytics/analytics-kpis';
import { AnalyticsLoading } from '@/components/admin/admin-analytics/analytics-states';
import { CompletionRateChart } from '@/components/admin/admin-analytics/completion-rate-chart';
import { DailyTrendChart } from '@/components/admin/admin-analytics/daily-trend-chart';
import { SourceBreakdown } from '@/components/admin/admin-analytics/source-breakdown';
import { SourcePerformance } from '@/components/admin/admin-analytics/source-performance';
import { StatusDistributionChart } from '@/components/admin/admin-analytics/status-distribution-chart';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PageNavigation } from '@/components/layout/page-navigation';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';

import { formatDateRange } from './analytics-format';

const periodLabels = {
  7: '最近 7 天',
  30: '最近 30 天',
  90: '最近 3 个月',
} as const;

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
    <div aria-busy={loading} className="flex flex-col gap-16 sm:gap-20">
      <div>
        <PageNavigation fallbackHref="/account" />
        <PageHeader
          action={
            <div className="flex flex-col gap-3 sm:items-end">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                {data ? (
                  <p className="text-xs text-muted-foreground tabular-nums">
                    {formatDateRange(data.start, data.end)}
                  </p>
                ) : null}
                <Select
                  value={String(days)}
                  onValueChange={(value) => {
                    if (value) onDaysChange(Number(value) as 7 | 30 | 90);
                  }}
                >
                  <SelectTrigger
                    aria-label="统计周期"
                    className="w-full sm:w-40"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {Object.entries(periodLabels).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
              <Button
                aria-label="刷新下载分析"
                className="w-full shrink-0 sm:w-auto"
                disabled={loading}
                onClick={onRetry}
                type="button"
                variant="outline"
              >
                {loading ? (
                  <Spinner aria-hidden data-icon="inline-start" />
                ) : (
                  <ArrowClockwiseIcon aria-hidden data-icon="inline-start" />
                )}
                <span className="hidden sm:inline">刷新</span>
              </Button>
            </div>
          }
          description="集中查看下载规模、完成质量与视频源表现。"
          title="下载分析"
        />
      </div>

      {error && !data ? (
        <PageErrorNotice
          message={error}
          onRetry={onRetry}
          title="无法加载下载分析"
        />
      ) : null}
      {error && data ? (
        <FeedbackNotice
          action={
            <Button onClick={onRetry} size="sm" variant="outline">
              重新加载
            </Button>
          }
          description={error}
          title="下载分析刷新失败"
          tone="error"
        />
      ) : null}

      {loading && !data ? <AnalyticsLoading /> : null}
      {data ? <DailyTrendChart daily={data.daily} /> : null}
      {data && data.summary.total > 0 ? (
        <div className="flex flex-col gap-20 sm:gap-28">
          <AnalyticsKpis summary={data.summary} />
          <div className="flex flex-col gap-20 sm:gap-28">
            <StatusDistributionChart summary={data.summary} />
            <CompletionRateChart daily={data.daily} />
            <SourceBreakdown
              sources={data.sources}
              total={data.summary.total}
            />
          </div>
          <SourcePerformance sources={data.sources} />
        </div>
      ) : null}
    </div>
  );
}
