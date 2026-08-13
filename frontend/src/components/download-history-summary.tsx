import { Skeleton } from '@/components/ui/skeleton';
import type { DownloadHistory } from '@/types/video';

type DownloadHistorySummaryProps = {
  data: DownloadHistory | null;
  loading: boolean;
};

export function DownloadHistorySummary({
  data,
  loading,
}: DownloadHistorySummaryProps) {
  return (
    <div
      aria-busy={loading}
      aria-live="polite"
      className="mt-12 h-[1.125rem] text-xs leading-[1.125rem] text-muted-foreground tabular-nums"
      data-slot="download-history-summary"
    >
      {data ? (
        <span>
          共 {data.total} 项 · 已完成 {data.summary.succeeded} · 进行中{' '}
          {data.summary.active}
        </span>
      ) : loading ? (
        <Skeleton aria-hidden className="h-full w-48" />
      ) : null}
    </div>
  );
}
