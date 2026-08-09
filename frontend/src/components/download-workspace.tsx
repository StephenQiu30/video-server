'use client';

import { useRouter } from 'next/navigation';
import { type RefObject, useEffect, useRef, useState } from 'react';

import DownloadHero from '@/components/download-hero';
import InspectionWorkspace from '@/components/inspection-workspace';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
      setUrl('https://www.bilibili.com/video/BV1D6u86fETf/');
      setInspection(demoInspection);
      setSelectedId(demoInspection.formats[0]?.id ?? '');
    }
  }, []);

  async function inspect() {
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

  async function create() {
    if (!inspection || !selectedId) return;
    setBusy('create');
    setError(null);
    try {
      const result = await createDownload(
        inspection.id,
        selectedId,
        stableKey(downloadKey, `${inspection.id}:${selectedId}`),
      );
      router.push(`/downloads/detail?jobId=${encodeURIComponent(result.id)}`);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="content-shell pb-4">
      <DownloadHero
        busy={busy === 'inspect'}
        inspection={inspection}
        onInspect={() => void inspect()}
        onUrlChange={setUrl}
        url={url}
      />
      {error ? (
        <Alert className="mb-7" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {inspection ? (
        <InspectionWorkspace
          busy={busy === 'create'}
          inspection={inspection}
          onChange={setSelectedId}
          onCreate={() => void create()}
          selectedId={selectedId}
        />
      ) : null}
      <p className="mt-24 text-center text-xs text-muted-foreground">
        帧取 · 合法合规的公开视频下载工具
      </p>
    </main>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
