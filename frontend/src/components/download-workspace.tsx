'use client';

import {
  ArrowClockwiseIcon,
  CheckCircleIcon,
  LinkSimpleIcon,
} from '@phosphor-icons/react';
import { useRouter } from 'next/navigation';
import {
  type FormEvent,
  type RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';

import InspectionView from '@/components/inspection-view';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { demoInspection } from '@/lib/demo-inspection';
import {
  createDownload,
  createIdempotencyKey,
  displayError,
  inspectMedia,
} from '@/services/download';
import type { Inspection } from '@/types/video';
import { normalizeMediaUrl, URL_MESSAGE } from '@/utils/validation';

type BusyAction = 'inspect' | 'create' | null;
type StableKey = { payload: string; value: string };

export default function DownloadWorkspace() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const inspectionKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);

  useEffect(() => {
    if (
      process.env.NODE_ENV !== 'production' &&
      new URLSearchParams(window.location.search).get('design') === 'inspection'
    ) {
      setUrl('https://www.bilibili.com/video/BV1x84y1d7QK/');
      setInspection(demoInspection);
      setSelectedId(demoInspection.formats[0].id);
    }
  }, []);

  async function handleInspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = normalizeMediaUrl(url);
    if (!normalized) {
      setError(URL_MESSAGE);
      return;
    }
    setBusy('inspect');
    setError(null);
    setInspection(null);
    setSelectedId('');
    try {
      const result = await inspectMedia(
        normalized,
        stableKey(inspectionKey, normalized),
      );
      setInspection(result);
      setSelectedId(result.formats[0]?.id ?? '');
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  async function handleCreate() {
    if (!inspection || !selectedId) return;
    setBusy('create');
    setError(null);
    try {
      const payload = `${inspection.id}:${selectedId}`;
      const result = await createDownload(
        inspection.id,
        selectedId,
        stableKey(downloadKey, payload),
      );
      router.push(`/downloads/?jobId=${encodeURIComponent(result.id)}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="page-shell">
      <section className="py-10 sm:py-12">
        <form
          className="flex flex-col overflow-hidden rounded-md border bg-background sm:flex-row sm:items-center"
          onSubmit={handleInspect}
        >
          <div className="relative min-w-0 flex-1">
            <LinkSimpleIcon className="absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              aria-label="公开视频地址"
              autoComplete="off"
              className="h-14 rounded-none border-0 pl-12 text-base shadow-none focus-visible:ring-0"
              maxLength={4096}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="粘贴 Bilibili、YouTube、抖音等公开视频链接"
              value={url}
            />
          </div>
          {inspection ? (
            <span className="flex shrink-0 items-center gap-1.5 px-4 text-sm font-medium text-emerald-600">
              <CheckCircleIcon weight="fill" /> 解析完成
            </span>
          ) : null}
          <Button
            className="h-14 rounded-none px-8 text-base"
            disabled={busy !== null}
            type="submit"
            variant="ghost"
          >
            {inspection ? (
              <ArrowClockwiseIcon data-icon="inline-start" />
            ) : null}
            {busy === 'inspect'
              ? '正在解析…'
              : inspection
                ? '重新解析'
                : '解析视频'}
          </Button>
        </form>
        {!inspection ? (
          <p className="mt-4 text-sm text-muted-foreground">
            支持 Bilibili、YouTube、抖音等 yt-dlp 可识别的公开来源
          </p>
        ) : null}
      </section>

      {error ? (
        <Alert className="mb-8" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {inspection ? (
        <InspectionView
          busy={busy === 'create'}
          inspection={inspection}
          onChange={setSelectedId}
          onCreate={handleCreate}
          selectedId={selectedId}
        />
      ) : (
        <EmptyHero loading={busy === 'inspect'} />
      )}
    </main>
  );
}

function EmptyHero({ loading }: { loading: boolean }) {
  return (
    <section className="technical-grid -mx-5 border-y px-5 py-24 sm:-mx-8 sm:px-8 lg:-mx-10 lg:px-10 lg:py-32">
      <p className="mb-4 text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
        Universal media workspace
      </p>
      <h1 className="max-w-4xl text-balance text-5xl leading-[0.96] font-semibold tracking-[-0.055em] sm:text-7xl lg:text-8xl">
        先确认内容，
        <br />
        再下载清晰原片
      </h1>
      <p className="mt-8 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">
        {loading
          ? '正在安全识别媒体信息和可用格式…'
          : '一个链接完成解析、格式选择、文件下载，并可在完成后继续生成摘要与思维导图。'}
      </p>
    </section>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
