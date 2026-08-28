import { Progress } from '@/components/ui/progress';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatPercent } from './analytics-format';

type Source = AdminDownloadAnalytics['sources'][number];

export function SourceBreakdown({
  sources,
  total,
}: {
  sources: Source[];
  total: number;
}) {
  const sorted = [...sources].sort((left, right) => right.total - left.total);
  const visible = sorted.slice(0, 6);
  const hiddenCount = Math.max(0, sorted.length - visible.length);

  return (
    <section
      aria-labelledby="source-breakdown-title"
      className="hairline xl:border-l xl:pl-10"
    >
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-lg font-medium" id="source-breakdown-title">
            来源分布
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            下载任务主要来自哪些平台。
          </p>
        </div>
        <p className="shrink-0 text-xs text-muted-foreground tabular-nums">
          {formatInteger(sorted.length)} 个来源
        </p>
      </div>
      {sorted.length === 0 ? (
        <p className="py-12 text-sm text-muted-foreground">暂无来源数据。</p>
      ) : (
        <ol className="mt-7 space-y-5">
          {visible.map((source) => {
            const share = total > 0 ? (source.total / total) * 100 : 0;
            return (
              <li key={source.source_key}>
                <div className="flex items-end justify-between gap-5">
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {source.source_name || source.source_key}
                    </p>
                    {source.source_name !== source.source_key ? (
                      <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                        {source.source_key}
                      </p>
                    ) : null}
                  </div>
                  <p className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    {formatInteger(source.total)} · {formatPercent(share)}
                  </p>
                </div>
                <meter
                  aria-label={`${source.source_name || source.source_key}占全部下载的${formatPercent(share)}`}
                  className="sr-only"
                  max={100}
                  min={0}
                  value={Number(share.toFixed(1))}
                >
                  {formatPercent(share)}
                </meter>
                <Progress
                  aria-hidden
                  className="mt-2 h-1.5"
                  value={Math.min(100, share)}
                />
              </li>
            );
          })}
        </ol>
      )}
      {hiddenCount > 0 ? (
        <p className="hairline mt-6 border-t pt-4 text-xs text-muted-foreground">
          其余 {formatInteger(hiddenCount)} 个来源可在下方明细中查看
        </p>
      ) : null}
    </section>
  );
}
