'use client';

import {
  type RefObject,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';

import {
  ContentIntakeHero,
  type IntakeMode,
} from '@/components/intake/content-intake-hero';
import InspectionWorkspace from '@/components/intake/inspection-workspace';
import { LinkDownloadForm } from '@/components/intake/link-download-form';
import { MediaUploadForm } from '@/components/intake/media-upload-form';
import { SourceDiscoveryWorkspace } from '@/components/intake/source-discovery-workspace';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { ScreenplayUploadForm } from '@/components/screenplay/screenplay-upload-form';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useDocumentImport } from '@/hooks/useDocumentImport';
import { useMediaImport } from '@/hooks/useMediaImport';
import { demoInspection } from '@/lib/demo-inspection';
import {
  createDownload,
  createIdempotencyKey,
  createSourceDiscovery,
  displayError,
  inspectDiscoveredItem,
  inspectMedia,
} from '@/services/download';
import type {
  Inspection,
  SourceDiscovery,
  SourceDiscoveryItem,
} from '@/types/video';
import { normalizeMediaUrl, URL_MESSAGE } from '@/utils/validation';

type BusyAction = 'inspect' | 'select' | 'create' | null;
type StableKey = { payload: string; value: string };

export default function DownloadWorkspace() {
  const [mode, setMode] = useState<IntakeMode>('link');
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [discovery, setDiscovery] = useState<SourceDiscovery | null>(null);
  const [busyItemRef, setBusyItemRef] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [urlInvalid, setUrlInvalid] = useState(false);
  const [mediaDeclaredOrigin, setMediaDeclaredOrigin] =
    useState<API.DeclaredOrigin>('user_file');
  const inspectionKey = useRef<StableKey | null>(null);
  const discoveryKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);
  const openDownload = useCallback((downloadId: string) => {
    const target = `/downloads/detail?jobId=${encodeURIComponent(downloadId)}`;
    markNavigationPush(target);
    window.location.assign(target);
  }, []);
  const openDocument = useCallback((documentId: string) => {
    const target = `/documents/detail?documentId=${encodeURIComponent(documentId)}`;
    markNavigationPush(target);
    window.location.assign(target);
  }, []);
  const mediaImport = useMediaImport(openDownload, mediaDeclaredOrigin);
  const documentImport = useDocumentImport(openDocument);

  function clearLinkResult() {
    setInspection(null);
    setDiscovery(null);
    setSelectedId('');
  }

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
    clearLinkResult();
    if (!normalized) {
      setUrlInvalid(true);
      setError(URL_MESSAGE);
      return;
    }
    setUrlInvalid(false);
    setBusy('inspect');
    setError(null);
    try {
      if (isWeChatArticleUrl(normalized)) {
        const result = await createSourceDiscovery(
          normalized,
          stableKey(discoveryKey, normalized),
        );
        setDiscovery(result);
      } else {
        const result = await inspectMedia(
          normalized,
          stableKey(inspectionKey, normalized),
        );
        setInspection(result);
        setSelectedId(result.formats[0]?.id ?? '');
      }
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  async function selectDiscoveredItem(item: SourceDiscoveryItem) {
    if (!discovery) return;
    setBusy('select');
    setBusyItemRef(item.item_ref);
    setError(null);
    setInspection(null);
    setSelectedId('');
    try {
      const result = await inspectDiscoveredItem(
        discovery.id,
        item.item_ref,
        stableKey(inspectionKey, `${discovery.id}:${item.item_ref}`),
      );
      setInspection(result);
      setSelectedId(result.formats[0]?.id ?? '');
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
      setBusyItemRef(null);
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
      openDownload(result.id);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="pb-6">
      <ContentIntakeHero
        disabled={busy !== null || mediaImport.busy || documentImport.busy}
        linkForm={
          <LinkDownloadForm
            busy={busy === 'inspect'}
            hasResult={inspection !== null || discovery !== null}
            invalid={urlInvalid}
            onInspect={() => void inspect()}
            onUrlChange={(value) => {
              setUrl(value);
              clearLinkResult();
              setUrlInvalid(false);
              setError(null);
            }}
            url={url}
          />
        }
        mode={mode}
        onModeChange={(nextMode) => {
          setMode(nextMode);
          if (nextMode === 'video') setMediaDeclaredOrigin('user_file');
        }}
        screenplayForm={
          <ScreenplayUploadForm
            busy={documentImport.busy}
            canCancel={documentImport.canCancel}
            error={documentImport.error}
            file={documentImport.file}
            fileInvalid={documentImport.fileInvalid}
            layout="workspace"
            onCancel={() => void documentImport.cancel()}
            onFileSelect={documentImport.selectFile}
            onStart={() => void documentImport.start()}
            phase={documentImport.phase}
            progress={documentImport.progress}
          />
        }
        videoForm={
          <MediaUploadForm
            busy={mediaImport.busy}
            canCancel={mediaImport.canCancel}
            file={mediaImport.file}
            fileInvalid={mediaImport.fileInvalid}
            onCancel={() => void mediaImport.cancel()}
            onFileSelect={mediaImport.selectFile}
            onStart={() => void mediaImport.start()}
            phase={mediaImport.phase}
            progress={mediaImport.progress}
            declaredOrigin={mediaDeclaredOrigin}
          />
        }
      />
      {(
        mode === 'link'
          ? error
          : mode === 'video'
            ? mediaImport.error
            : null
      ) ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription id="download-workspace-error">
            {mode === 'link' ? error : mediaImport.error}
          </AlertDescription>
        </Alert>
      ) : null}
      {mode === 'video' && mediaImport.notice ? (
        <Alert className="mt-8">
          <AlertTitle>上传已取消</AlertTitle>
          <AlertDescription>{mediaImport.notice}</AlertDescription>
        </Alert>
      ) : null}
      {mode === 'link' && discovery ? (
        <SourceDiscoveryWorkspace
          busyItemRef={busyItemRef}
          discovery={discovery}
          onSelect={(item) => void selectDiscoveredItem(item)}
        />
      ) : null}
      {mode === 'link' && inspection ? (
        <InspectionWorkspace
          busy={busy === 'create'}
          inspection={inspection}
          onChange={setSelectedId}
          onCreate={() => void create()}
          onUseUpload={() => {
            setMediaDeclaredOrigin('wechat_channels');
            setMode('video');
          }}
          selectedId={selectedId}
        />
      ) : null}
    </div>
  );
}

function isWeChatArticleUrl(value: string) {
  try {
    const parsed = new URL(value);
    return (
      parsed.protocol === 'https:' && parsed.hostname === 'mp.weixin.qq.com'
    );
  } catch {
    return false;
  }
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
