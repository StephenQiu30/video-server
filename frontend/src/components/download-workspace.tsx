'use client';

import { CheckCircle, ShieldCheck } from '@phosphor-icons/react';
import { type RefObject, useEffect, useRef, useState } from 'react';

import DownloadHero from '@/components/download-hero';
import InspectionWorkspace from '@/components/inspection-workspace';
import { markNavigationPush } from '@/components/navigation-history';
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
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [urlInvalid, setUrlInvalid] = useState(false);
  const inspectionKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);

  useEffect(() => {
    if (
      process.env.NODE_ENV !== 'production' &&
      new URLSearchParams(window.location.search).get('design') === 'inspection'
    ) {
      setUrl('https://media.example/alpine-lake');
      setInspection(demoInspection);
      setSelectedId(demoInspection.formats[0]?.id ?? '');
    }
  }, []);

  async function inspect() {
    const normalized = normalizeMediaUrl(url);
    if (!normalized) {
      setUrlInvalid(true);
      setError(URL_MESSAGE);
      return;
    }
    setUrlInvalid(false);
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
    setUrlInvalid(false);
    setBusy('create');
    setError(null);
    try {
      const result = await createDownload(
        inspection.id,
        selectedId,
        stableKey(downloadKey, `${inspection.id}:${selectedId}`),
      );
      const target = `/downloads/detail?jobId=${encodeURIComponent(result.id)}`;
      markNavigationPush(target);
      window.location.assign(target);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="content-shell pb-6">
      <DownloadHero
        busy={busy === 'inspect'}
        inspection={inspection}
        invalid={urlInvalid}
        onInspect={() => void inspect()}
        onUrlChange={(value) => {
          setUrl(value);
          if (urlInvalid) {
            setUrlInvalid(false);
            setError(null);
          }
        }}
        url={url}
      />
      {error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription id="download-workspace-error">
            {error}
          </AlertDescription>
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
      <footer className="mt-10 flex flex-col gap-3 border-t py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-2">
          <CheckCircle aria-hidden className="size-4 text-success" />
          公开链接 · 无 DRM · 安全解析
        </span>
        <span className="flex items-center gap-1.5">
          <ShieldCheck aria-hidden className="size-4" />
          隐私保护
        </span>
      </footer>
    </main>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
