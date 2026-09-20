'use client';

import { useRouter } from 'next/navigation';
import { type RefObject, useCallback, useRef, useState } from 'react';
import { createDownload } from '@/api/downloads';
import {
  inspectMedia as inspectDiscoveredItem,
  inspectMedia,
} from '@/api/inspections';
import { createSourceDiscovery } from '@/api/sourceDiscoveries';
import {
  ContentIntakeHero,
  type IntakeMode,
} from '@/components/intake/content-intake-hero';
import InspectionWorkspace from '@/components/intake/inspection-workspace';
import { LinkDownloadForm } from '@/components/intake/link-download-form';
import { MediaUploadForm } from '@/components/intake/media-upload-form';
import {
  hasPublicInput,
  isWeChatArticleInput,
  PUBLIC_INPUT_REQUIRED,
} from '@/components/intake/public-input';
import { SourceDiscoveryWorkspace } from '@/components/intake/source-discovery-workspace';
import { useDocumentImport } from '@/components/intake/use-document-import';
import { useMediaImport } from '@/components/intake/use-media-import';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { ScreenplayUploadForm } from '@/components/screenplay/screenplay-upload-form';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { displayError } from '@/lib/request-error';
import { createUuid as createIdempotencyKey } from '@/lib/uuid';

type BusyAction = 'inspect' | 'select' | 'create' | null;
type StableKey = { payload: string; value: string };

export default function DownloadWorkspace() {
  const router = useRouter();
  const [mode, setMode] = useState<IntakeMode>('link');
  const [url, setUrl] = useState('');
  const [inspection, setInspection] = useState<API.InspectionResponse | null>(
    null,
  );
  const [discovery, setDiscovery] =
    useState<API.SourceDiscoveryResponse | null>(null);
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
  const openDownload = useCallback(
    (downloadId: string) => {
      const target = `/downloads/detail?jobId=${encodeURIComponent(
        downloadId,
      )}`;
      markNavigationPush(target);
      router.push(target);
    },
    [router],
  );
  const openDocument = useCallback(
    (documentId: string) => {
      const target = `/documents/detail?documentId=${encodeURIComponent(
        documentId,
      )}`;
      markNavigationPush(target);
      router.push(target);
    },
    [router],
  );
  const mediaImport = useMediaImport(openDownload, mediaDeclaredOrigin);
  const documentImport = useDocumentImport(openDocument);

  function clearLinkResult() {
    setInspection(null);
    setDiscovery(null);
    setSelectedId('');
  }

  async function inspect() {
    if (busy !== null) return;
    const input = url.trim();
    clearLinkResult();
    if (!hasPublicInput(input)) {
      setUrlInvalid(true);
      setError(PUBLIC_INPUT_REQUIRED);
      return;
    }
    setUrlInvalid(false);
    setBusy('inspect');
    setError(null);
    try {
      if (isWeChatArticleInput(input)) {
        const result = await createSourceDiscovery(
          { kind: 'wechat_official_account_article', url: input },
          {
            headers: { 'Idempotency-Key': stableKey(discoveryKey, input) },
            timeout: 30_000,
          },
        );
        setDiscovery(result);
      } else {
        const result = await inspectMedia(
          { source: { kind: 'public_url', url: input } },
          {
            headers: { 'Idempotency-Key': stableKey(inspectionKey, input) },
            timeout: 180_000,
          },
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

  async function selectDiscoveredItem(item: API.SourceDiscoveryItemResponse) {
    if (!discovery || busy !== null) return;
    setBusy('select');
    setBusyItemRef(item.item_ref);
    setError(null);
    setInspection(null);
    setSelectedId('');
    try {
      const result = await inspectDiscoveredItem(
        {
          source: {
            kind: 'discovered_item',
            discovery_id: discovery.id,
            item_ref: item.item_ref,
          },
        },
        {
          headers: {
            'Idempotency-Key': stableKey(
              inspectionKey,
              `${discovery.id}:${item.item_ref}`,
            ),
          },
          timeout: 30_000,
        },
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
    if (!inspection || !selectedId || busy !== null) return;
    setUrlInvalid(false);
    setBusy('create');
    setError(null);
    try {
      const result = await createDownload(
        {
          inspection_id: inspection.id,
          format_id: selectedId,
        },
        {
          headers: {
            'Idempotency-Key': stableKey(
              downloadKey,
              `${inspection.id}:${selectedId}`,
            ),
          },
        },
      );
      openDownload(result.id);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="pb-6" data-slot="download-workspace">
      <ContentIntakeHero
        disabled={busy !== null || mediaImport.busy || documentImport.busy}
        linkForm={
          <LinkDownloadForm
            busy={busy === 'inspect'}
            disabled={busy !== null}
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
      <div
        aria-atomic="true"
        aria-live="polite"
        className="sr-only"
        role="status"
      >
        {mode === 'link'
          ? inspection
            ? '媒体解析完成，结果已显示。'
            : discovery
              ? `来源发现完成，找到 ${discovery.items.length} 个候选视频。`
              : null
          : null}
      </div>
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
          key={`discovery:${discovery.id}`}
          onSelect={(item) => void selectDiscoveredItem(item)}
        />
      ) : null}
      {mode === 'link' && inspection ? (
        <InspectionWorkspace
          busy={busy === 'create'}
          inspection={inspection}
          key={`inspection:${inspection.id}`}
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

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
