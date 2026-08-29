import { Fragment } from 'react';

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemFooter,
  ItemGroup,
  ItemSeparator,
  ItemTitle,
} from '@/components/ui/item';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatBytes, formatInteger, formatPercent } from './analytics-format';

type Source = AdminDownloadAnalytics['sources'][number];

export function SourcePerformanceDetails({ sources }: { sources: Source[] }) {
  return (
    <>
      <div className="hairline mt-7 hidden border-y md:block">
        <Table className="table-fixed">
          <TableCaption className="sr-only">各视频源下载表现</TableCaption>
          <TableHeader className="bg-muted/35">
            <TableRow className="hairline hover:bg-transparent">
              <SourceHead className="w-[20%]">视频源</SourceHead>
              <SourceHead className="w-[10%]" numeric>
                任务
              </SourceHead>
              <SourceHead className="w-[11%]" numeric>
                成功率
              </SourceHead>
              <SourceHead className="w-[11%]" numeric>
                用户
              </SourceHead>
              <SourceHead className="w-[15%]" numeric>
                数据量
              </SourceHead>
              <SourceHead className="w-[33%]">状态分布</SourceHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources.map((source) => (
              <TableRow className="hairline" key={source.source_key}>
                <th
                  className="px-4 py-5 text-left align-middle whitespace-normal"
                  scope="row"
                >
                  <p className="truncate font-medium">{sourceLabel(source)}</p>
                  <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">
                    {source.source_key}
                  </p>
                </th>
                <MetricCell value={formatInteger(source.total)} />
                <MetricCell value={formatPercent(source.success_rate)} />
                <MetricCell value={formatInteger(source.unique_users)} />
                <MetricCell value={formatBytes(source.downloaded_bytes)} />
                <TableCell className="px-4 py-5 whitespace-normal">
                  <StatusSummary source={source} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ItemGroup className="hairline mt-7 gap-0 border-y md:hidden">
        {sources.map((source, index) => (
          <Fragment key={source.source_key}>
            <Item className="rounded-none border-0 px-0 py-5" role="listitem">
              <ItemContent className="min-w-0">
                <ItemTitle className="truncate">
                  {sourceLabel(source)}
                </ItemTitle>
                <ItemDescription className="truncate font-mono text-[11px]">
                  {source.source_key}
                </ItemDescription>
              </ItemContent>
              <ItemActions className="text-sm tabular-nums">
                {formatPercent(source.success_rate)}
              </ItemActions>
              <ItemFooter className="grid w-full gap-3">
                <p className="text-xs text-muted-foreground">
                  {formatInteger(source.total)} 个任务 ·{' '}
                  {formatInteger(source.unique_users)} 位用户 ·{' '}
                  {formatBytes(source.downloaded_bytes)}
                </p>
                <StatusSummary source={source} />
              </ItemFooter>
            </Item>
            {index < sources.length - 1 ? (
              <ItemSeparator className="hairline my-0" />
            ) : null}
          </Fragment>
        ))}
      </ItemGroup>
    </>
  );
}

function SourceHead({
  children,
  className,
  numeric = false,
}: {
  children: React.ReactNode;
  className: string;
  numeric?: boolean;
}) {
  return (
    <TableHead
      className={`${className} px-4 text-xs font-normal text-muted-foreground ${numeric ? 'text-right tabular-nums' : ''}`}
      scope="col"
    >
      {children}
    </TableHead>
  );
}

function MetricCell({ value }: { value: string }) {
  return (
    <TableCell className="px-4 py-5 text-right text-xs tabular-nums whitespace-normal">
      {value}
    </TableCell>
  );
}

function StatusSummary({ source }: { source: Source }) {
  return (
    <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground tabular-nums">
      <span className="text-success">成功 {source.succeeded}</span>
      <span className="text-destructive">失败 {source.failed}</span>
      <span>取消 {source.cancelled}</span>
      <span className="text-warning">进行中 {source.active}</span>
    </span>
  );
}

function sourceLabel(source: Source): string {
  return source.source_name || source.source_key;
}
