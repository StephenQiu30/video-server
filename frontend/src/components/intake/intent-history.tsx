'use client';

import { ArrowClockwise, ClockCounterClockwise } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import { useId, useRef, useState } from 'react';
import { listDownloadIntents } from '@/api/downloadIntents';
import { intentTitle } from '@/components/intake/intent-status';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

// History only locates existing owner-bound resources. Selecting a row never
// posts a new parse request or changes its deadline.
export function IntentHistory({
  disabled,
  onResume,
}: {
  disabled: boolean;
  onResume: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [cursors, setCursors] = useState<(string | undefined)[]>([undefined]);
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const before = cursors.at(-1);
  const history = useQuery({
    queryKey: privateQueryKey('intent-history', before),
    enabled: open,
    queryFn: ({ signal }) =>
      listDownloadIntents({ before, limit: 20 }, { signal }),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
  return (
    <section aria-label="解析记录" className="mt-4">
      <Button
        ref={trigger}
        variant="ghost"
        aria-controls={id}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <ClockCounterClockwise aria-hidden data-icon="inline-start" />
        解析记录
      </Button>
      <div id={id} hidden={!open} className="mt-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-medium">继续之前的解析</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              关闭页面或更换设备后，可在这里找回当前账户的任务。
            </p>
          </div>
          <Button
            variant="ghost"
            aria-label="刷新解析记录"
            disabled={history.isFetching}
            onClick={() => void history.refetch()}
          >
            <ArrowClockwise aria-hidden />
          </Button>
        </div>
        {history.isPending ? (
          <p role="status" className="py-8 text-sm text-muted-foreground">
            正在读取解析记录…
          </p>
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
            description="粘贴媒体链接并点击解析后，可在这里继续查看。"
          />
        ) : null}
        <ItemGroup className="mt-4" aria-label="已提交的解析">
          {history.data?.items.map((item) => (
            <Item key={item.id} role="listitem" className="px-0">
              <ItemContent className="min-w-0">
                <ItemTitle className="break-words">
                  {item.title || '媒体解析'}
                </ItemTitle>
                <ItemDescription>
                  <time dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString('zh-CN', {
                      hour12: false,
                    })}
                  </time>
                  {' · '}
                  {intentTitle(item.status)}
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  variant="outline"
                  disabled={disabled}
                  onClick={() => {
                    onResume(item.id);
                    setOpen(false);
                    trigger.current?.focus();
                  }}
                >
                  查看解析
                </Button>
              </ItemActions>
            </Item>
          ))}
        </ItemGroup>
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
      </div>
    </section>
  );
}
