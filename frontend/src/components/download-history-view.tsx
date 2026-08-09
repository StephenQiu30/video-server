'use client';

import { ArrowClockwise, MagnifyingGlass, Plus } from '@phosphor-icons/react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import DownloadHistoryList, {
  downloadStatusLabels,
} from '@/components/download-history-list';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDownloadHistory } from '@/hooks/useDownloadHistory';
import {
  displayError,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';

export default function DownloadHistoryView() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [actionError, setActionError] = useState<string | null>(null);
  const state = useDownloadHistory({
    page,
    page_size: 20,
    search: search || undefined,
    status,
  });

  async function download(item: DownloadHistoryItem) {
    setActionError(null);
    try {
      triggerBrowserDownload((await issueDownloadUrl(item.id)).url);
    } catch (reason) {
      setActionError(displayError(reason));
    }
  }

  return (
    <main className="content-shell py-12 sm:py-16">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-sm font-medium text-primary">任务记录</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.035em]">
            下载历史
          </h1>
          <p className="mt-3 text-muted-foreground">
            继续查看、获取或分析已创建的任务。
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/">
            <Plus size={17} />
            新建下载
          </Link>
        </Button>
      </div>

      <div className="mt-11 flex flex-col gap-3 border-y py-5 sm:flex-row">
        <form
          className="relative flex-1"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(searchInput.trim());
          }}
        >
          <MagnifyingGlass className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label="搜索下载历史"
            className="pl-9"
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="按视频标题搜索"
            value={searchInput}
          />
        </form>
        <Select
          onValueChange={(value) => {
            setPage(1);
            setStatus(value === 'all' ? undefined : (value as DownloadStatus));
          }}
          value={status ?? 'all'}
        >
          <SelectTrigger aria-label="按状态筛选" className="sm:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(downloadStatusLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={state.retry} variant="outline">
          <ArrowClockwise size={17} />
          刷新
        </Button>
      </div>

      {state.data ? (
        <p className="mt-6 text-sm text-muted-foreground">
          共 {state.data.total} 项 · 已完成 {state.data.summary.succeeded} ·
          进行中 {state.data.summary.active}
        </p>
      ) : null}
      {state.error || actionError ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{state.error ?? actionError}</AlertDescription>
        </Alert>
      ) : null}

      <DownloadHistoryList
        data={state.data}
        loading={state.loading}
        onDownload={(item) => void download(item)}
        onOpen={(id) =>
          router.push(`/downloads/detail?jobId=${encodeURIComponent(id)}`)
        }
      />

      {state.data && state.data.total > state.data.page_size ? (
        <div className="mt-8 flex items-center justify-end gap-3">
          <Button
            disabled={page <= 1}
            onClick={() => setPage((value) => value - 1)}
            variant="outline"
          >
            上一页
          </Button>
          <span className="font-mono text-sm text-muted-foreground">
            第 {page} 页
          </span>
          <Button
            disabled={page * state.data.page_size >= state.data.total}
            onClick={() => setPage((value) => value + 1)}
            variant="outline"
          >
            下一页
          </Button>
        </div>
      ) : null}
    </main>
  );
}
