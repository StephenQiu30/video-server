'use client';

import { ArrowClockwise, Plus } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useRef, useState } from 'react';
import { listHistoryRecords } from '@/api/downloadIntents';
import { useAnalysisSkills } from '@/components/analysis/use-analysis-skills';
import {
  analysisStatusVariant,
  isActiveAnalysisStatus,
  statusLabels,
} from '@/components/analysis/analysis-panel-model';
import { IntentHistoryDialog } from '@/components/intake/intent-history-dialog';
import {
  IntentStatusCode,
  intentHistoryActionLabel,
  intentStatusVariant,
  intentTitle,
} from '@/components/intake/intent-status';
import { BackLink } from '@/components/layout/back-link';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';
import { Skeleton } from '@/components/ui/skeleton';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

// History only locates existing owner-bound resources. Selecting a row never
// posts a new parse request or changes its deadline.
export function IntentHistory({
  onViewResult,
}: {
  onViewResult: (item: API.IntentHistoryItemResponse) => void;
}) {
  type ParseHistoryItem = API.ParseHistoryRecordResponse;
  const [cursors, setCursors] = useState<
    (API.HistoryRecordCursorResponse | undefined)[]
  >([undefined]);
  const [selected, setSelected] = useState<ParseHistoryItem | null>(null);
  const detailTrigger = useRef<HTMLButtonElement | null>(null);
  const before = cursors.at(-1);
  const history = useQuery({
    queryKey: privateQueryKey(
      'intent-history',
      before?.created_at,
      before?.record_type,
      before?.id,
    ),
    queryFn: ({ signal }) =>
      listHistoryRecords(
        {
          before_created_at: before?.created_at,
          before_record_type: before?.record_type,
          before_id: before?.id,
          limit: 20,
        },
        { signal },
      ),
    staleTime: 0,
    refetchInterval: (query) =>
      query.state.error
        ? false
        : query.state.data?.items.some(
              (item) =>
                isVideoAnalysisRecord(item) &&
                isActiveAnalysisStatus(item.status),
            )
          ? 2_000
          : false,
    refetchOnWindowFocus: true,
  });
  const analysisSkills = useAnalysisSkills();
  const skillNames = new Map(
    analysisSkills.skills.map((skill) => [skill.id, skill.display_name]),
  );
  return (
    <div className="inner-page">
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        action={
          <Button asChild size="lg">
            <Link href="/">
              <Plus data-icon="inline-start" />
              新建解析
            </Link>
          </Button>
        }
        description="查看之前提交的解析，以及针对视频运行过的 Skill 分析。"
        title="解析记录"
      />
      <section aria-label="已提交的解析" className="mt-12 lg:mt-16">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-base font-medium">解析任务</h2>
          <Button
            variant="outline"
            disabled={history.isFetching}
            onClick={() => void history.refetch()}
          >
            <ArrowClockwise data-icon="inline-start" />
            {history.isFetching ? '更新中…' : '刷新'}
          </Button>
        </div>
        {history.isPending ? (
          <>
            <span className="sr-only" role="status">
              正在读取解析记录…
            </span>
            <div aria-hidden className="mt-4 flex flex-col gap-2">
              {['first', 'second', 'third'].map((key) => (
                <div
                  className="flex items-center justify-between gap-4 py-5"
                  key={key}
                >
                  <div className="flex min-w-0 flex-1 flex-col gap-2">
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                  <Skeleton className="h-7 w-24" />
                </div>
              ))}
            </div>
          </>
        ) : null}
        {history.error && !history.data ? (
          <PageErrorNotice
            compact
            title="暂时无法读取解析记录"
            message={displayError(history.error)}
            onRetry={() => void history.refetch()}
          />
        ) : null}
        {history.error && history.data ? (
          <FeedbackNotice
            className="mt-4"
            title="解析记录刷新失败"
            description={displayError(history.error)}
            tone="error"
          />
        ) : null}
        {history.data?.items.length === 0 ? (
          <PageEmptyNotice
            compact
            title="暂无解析记录"
            description="提交媒体解析或运行视频 Skill 后，可在这里继续查看。"
          />
        ) : null}
        {history.data?.items.length ? (
          <>
            <div
              aria-hidden
              className="mt-6 hidden grid-cols-[minmax(0,1fr)_11rem_10rem_7rem] gap-6 text-xs text-muted-foreground lg:grid"
            >
              <span>内容</span>
              <span>提交时间</span>
              <span>状态</span>
              <span className="text-right">操作</span>
            </div>
            <ItemGroup className="mt-2 gap-2" aria-label="解析任务列表">
              {history.data.items.map((item) => (
                <Item
                  key={`${item.record_type}:${item.id}`}
                  role="listitem"
                  className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-none border-0 px-0 py-5 lg:grid-cols-[minmax(0,1fr)_11rem_10rem_7rem] lg:gap-x-6"
                >
                  <ItemContent className="col-span-2 min-w-0 lg:col-span-1">
                    <ItemTitle className="line-clamp-2 w-auto break-words text-[15px]">
                      {item.title || '媒体解析'}
                    </ItemTitle>
                    {isVideoAnalysisRecord(item) ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        视频分析 ·{' '}
                        {skillNames.get(item.skill_id) ?? item.skill_id}
                      </p>
                    ) : null}
                  </ItemContent>
                  <time
                    className="text-xs text-muted-foreground sm:text-sm"
                    dateTime={item.created_at}
                  >
                    {new Date(item.created_at).toLocaleString('zh-CN', {
                      hour12: false,
                    })}
                  </time>
                  <Badge
                    className="justify-self-end rounded-md px-2 py-1 font-normal lg:justify-self-start"
                    variant={
                      isVideoAnalysisRecord(item)
                        ? analysisStatusVariant(item.status)
                        : intentStatusVariant(item.status)
                    }
                  >
                    {isVideoAnalysisRecord(item)
                      ? `${statusLabels[item.status]}${isActiveAnalysisStatus(item.status) ? ` · ${item.progress}%` : ''}`
                      : intentTitle(item.status)}
                  </Badge>
                  <ItemActions className="col-span-2 justify-end lg:col-span-1">
                    {isVideoAnalysisRecord(item) ? (
                      <Button asChild variant="ghost" size="sm">
                        <Link
                          href={
                            item.download_id
                              ? `/downloads/detail?jobId=${encodeURIComponent(item.download_id)}&analysisId=${encodeURIComponent(item.id)}`
                              : `/downloads/detail?analysisId=${encodeURIComponent(item.id)}`
                          }
                        >
                          查看分析
                        </Link>
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(event) => {
                          if (
                            item.status === IntentStatusCode.Ready &&
                            item.inspection_id
                          ) {
                            onViewResult(item);
                            return;
                          }
                          detailTrigger.current = event.currentTarget;
                          setSelected(item);
                        }}
                      >
                        {intentHistoryActionLabel(item.status)}
                      </Button>
                    )}
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </>
        ) : null}
        {cursors.length > 1 || history.data?.next_cursor ? (
          <nav
            className="mt-4 flex justify-end gap-2"
            aria-label="解析记录分页"
          >
            <Button
              variant="ghost"
              disabled={cursors.length <= 1 || history.isFetching}
              onClick={() => setCursors((value) => value.slice(0, -1))}
            >
              较新的记录
            </Button>
            <Button
              variant="ghost"
              disabled={!history.data?.next_cursor || history.isFetching}
              onClick={() => {
                if (history.data?.next_cursor)
                  setCursors((value) => [
                    ...value,
                    history.data?.next_cursor ?? undefined,
                  ]);
              }}
            >
              更早的记录
            </Button>
          </nav>
        ) : null}
      </section>
      <IntentHistoryDialog
        item={selected}
        onClose={() => setSelected(null)}
        triggerRef={detailTrigger}
      />
    </div>
  );
}

function isVideoAnalysisRecord(
  item: API.HistoryRecordPageResponse['items'][number],
): item is API.VideoAnalysisHistoryRecordResponse {
  return item.record_type === 'video_analysis';
}
