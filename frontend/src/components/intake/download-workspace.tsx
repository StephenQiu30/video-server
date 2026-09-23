'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  type RefObject,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import { toast } from 'sonner';
import { createDownload } from '@/api/downloads';
import {
  inspectMedia as inspectDiscoveredItem,
  inspectMedia,
} from '@/api/inspections';
import { createSourceDiscovery } from '@/api/sourceDiscoveries';
import { ContentIntakeHero } from '@/components/intake/content-intake-hero';
import InspectionWorkspace from '@/components/intake/inspection-workspace';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import { intentTitle } from '@/components/intake/intent-status';
import { LinkDownloadForm } from '@/components/intake/link-download-form';
import { MediaUploadForm } from '@/components/intake/media-upload-form';
import {
  hasPublicInput,
  isWeChatArticleInput,
  PUBLIC_INPUT_REQUIRED,
} from '@/components/intake/public-input';
import { SourceDiscoveryWorkspace } from '@/components/intake/source-discovery-workspace';
import { useDocumentImport } from '@/components/intake/use-document-import';
import { useDownloadIntent } from '@/components/intake/use-download-intent';
import { useMediaImport } from '@/components/intake/use-media-import';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { ProviderAuthorizationDialog } from '@/components/providers/provider-authorization-dialog';
import { ScreenplayUploadForm } from '@/components/screenplay/screenplay-upload-form';
import { Button } from '@/components/ui/button';
import { localizedErrorMessage } from '@/lib/error-messages';
import {
  type ProviderAuthorizationTarget,
  providerAuthorizationTarget,
} from '@/lib/provider-authorization';
import { privateQueryKey } from '@/lib/query-keys';
import { ApiError, displayError } from '@/lib/request-error';
import { createUuid as createIdempotencyKey } from '@/lib/uuid';

type BusyAction = 'inspect' | 'select' | 'create' | null;
type StableKey = { payload: string; value: string };

export default function DownloadWorkspace() {
  const router = useRouter();
  const queries = useQueryClient();
  const {
    mode,
    setMode,
    input: url,
    setInput: setUrl,
    declaredOrigin: mediaDeclaredOrigin,
    setDeclaredOrigin: setMediaDeclaredOrigin,
    selectedFormatId,
    setSelectedFormatId: setSelectedId,
  } = useIntakeDraft();
  const intent = useDownloadIntent();
  const [localInspection, setInspection] =
    useState<API.InspectionResponse | null>(null);
  const inspection = localInspection ?? intent.inspection ?? null;
  const selectedId = inspection?.formats.some(
    (item) => item.id === selectedFormatId,
  )
    ? selectedFormatId
    : inspection?.formats[0]?.id || '';
  const [discovery, setDiscovery] =
    useState<API.SourceDiscoveryResponse | null>(null);
  const [busyItemRef, setBusyItemRef] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [authorizationTarget, setAuthorizationTarget] =
    useState<ProviderAuthorizationTarget | null>(null);
  const intentAuthorization =
    intent.snapshot?.status === 'failed' && intent.snapshot.reason_code
      ? providerAuthorizationTarget(url, intent.snapshot.reason_code)
      : null;
  const [urlInvalid, setUrlInvalid] = useState(false);
  const inspectionKey = useRef<StableKey | null>(null);
  const discoveryKey = useRef<StableKey | null>(null);
  const downloadKey = useRef<StableKey | null>(null);
  const openDownload = useCallback(
    (downloadId: string) => {
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
      const target = `/downloads/detail?jobId=${encodeURIComponent(
        downloadId,
      )}`;
      markNavigationPush(target);
      router.push(target);
    },
    [queries, router],
  );
  const openDocument = useCallback(
    (documentId: string) => {
      void queries.invalidateQueries({
        queryKey: privateQueryKey('documents'),
      });
      const target = `/documents/detail?documentId=${encodeURIComponent(
        documentId,
      )}`;
      markNavigationPush(target);
      router.push(target);
    },
    [queries, router],
  );
  const mediaImport = useMediaImport(openDownload, mediaDeclaredOrigin);
  const documentImport = useDocumentImport(openDocument);

  useEffect(() => {
    if (mediaImport.notice) toast.info(mediaImport.notice);
  }, [mediaImport.notice]);

  function clearLinkResult() {
    if (!intent.pending) intent.clear();
    setInspection(null);
    setDiscovery(null);
    setSelectedId('');
    setAuthorizationTarget(null);
  }

  async function inspect(accessPolicy?: API.ProviderAccessPolicy) {
    if (busy !== null || (intent.pending && !intent.canResubmit)) return;
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
      } else if (accessPolicy) {
        const source: API.PublicUrlInspectionSource = {
          kind: 'public_url',
          url: input,
          ...(accessPolicy ? { access_policy_id: accessPolicy } : {}),
        };
        const result = await inspectMedia(
          { source },
          {
            headers: {
              'Idempotency-Key': stableKey(
                inspectionKey,
                `${input}:${accessPolicy ?? 'default'}`,
              ),
            },
            timeout: 180_000,
          },
        );
        setInspection(result);
        setSelectedId(result.formats[0]?.id ?? '');
      } else {
        await intent.submit(input, intent.canResubmit);
      }
    } catch (reason) {
      setAuthorizationTarget(
        reason instanceof ApiError
          ? providerAuthorizationTarget(input, reason.code)
          : null,
      );
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
      setAuthorizationTarget(null);
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
      queries.setQueryData(privateQueryKey('download', result.id), result);
      openDownload(result.id);
    } catch (reason) {
      setAuthorizationTarget(null);
      if (
        reason instanceof ApiError &&
        reason.code === 'resource_expired' &&
        intent.snapshot?.status === 'ready'
      ) {
        setSelectedId('');
        await intent.refresh();
        return;
      }
      setError(displayError(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="pb-6" data-slot="download-workspace">
      <ContentIntakeHero
        disabled={
          busy !== null ||
          intent.pending ||
          mediaImport.busy ||
          documentImport.busy
        }
        linkForm={
          <LinkDownloadForm
            busy={busy === 'inspect' || (intent.pending && !intent.canResubmit)}
            disabled={busy !== null || (intent.pending && !intent.canResubmit)}
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
      {mode === 'link' && intent.attempt ? (
        <section className="mt-8 space-y-3" aria-label="解析任务状态">
          <FeedbackNotice
            title={
              intent.error
                ? '任务状态暂时无法更新'
                : intent.pending && intent.snapshot?.status === 'ready'
                  ? '正在更新解析结果'
                  : intent.resultExpired
                    ? '解析结果已过期'
                    : intentTitle(intent.snapshot?.status)
            }
            description={
              intent.error ??
              (intent.resultExpired
                ? '更新后请重新确认下载规格，无需再次粘贴原链接。'
                : null) ??
              (intent.snapshot?.reason_code
                ? localizedErrorMessage(intent.snapshot.reason_code)
                : null) ??
              (!intent.snapshot
                ? '正在确认接单，请稍候，无需重复提交。'
                : intent.pending
                  ? '任务已在后台处理，切换页面不会中断解析。'
                  : intent.snapshot?.status === 'ready'
                    ? '解析完成，请选择需要的下载规格。'
                    : intent.snapshot?.status === 'handed_off'
                      ? '已创建下载任务，可继续查看进度。'
                      : '本次解析已结束。')
            }
            tone={
              intent.error ||
              intent.snapshot?.status === 'failed' ||
              intent.snapshot?.status === 'expired'
                ? 'error'
                : 'info'
            }
          />
          <div className="flex flex-wrap gap-2">
            {intent.resultExpired ? (
              <Button
                disabled={intent.pending}
                onClick={() => {
                  setSelectedId('');
                  void intent.refresh();
                }}
              >
                更新解析结果
              </Button>
            ) : null}
            {intentAuthorization ? (
              <ProviderAuthorizationDialog
                onAuthorized={() => inspect(intentAuthorization.accessPolicy)}
                provider={{
                  authorization_action: intentAuthorization.authorizationAction,
                  display_name: intentAuthorization.displayName,
                  key: intentAuthorization.key,
                }}
              />
            ) : null}
            {intent.error ? (
              <Button variant="outline" onClick={() => void intent.retry()}>
                恢复任务
              </Button>
            ) : null}
            {intent.snapshot &&
            (intent.pending || intent.snapshot.status === 'action_required') ? (
              <Button
                variant="outline"
                disabled={intent.cancelling}
                onClick={() => void intent.cancel()}
              >
                {intent.cancelling ? '正在取消…' : '取消解析'}
              </Button>
            ) : null}
            {intent.snapshot?.job_id ? (
              <Button
                onClick={() => openDownload(intent.snapshot?.job_id ?? '')}
              >
                查看下载任务
              </Button>
            ) : null}
          </div>
        </section>
      ) : null}
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
        <FeedbackNotice
          action={
            mode === 'link' && authorizationTarget ? (
              <ProviderAuthorizationDialog
                onAuthorized={() => {
                  return inspect(authorizationTarget.accessPolicy);
                }}
                provider={{
                  authorization_action: authorizationTarget.authorizationAction,
                  display_name: authorizationTarget.displayName,
                  key: authorizationTarget.key,
                }}
              />
            ) : undefined
          }
          className="mt-8"
          description={mode === 'link' ? error : mediaImport.error}
          descriptionId="download-workspace-error"
          title="操作未完成"
          tone="error"
        />
      ) : null}
      {mode === 'link' && discovery ? (
        <SourceDiscoveryWorkspace
          busyItemRef={busyItemRef}
          discovery={discovery}
          key={`discovery:${discovery.id}`}
          onSelect={(item) => void selectDiscoveredItem(item)}
        />
      ) : null}
      {mode === 'link' &&
      inspection &&
      !intent.resultExpired &&
      intent.snapshot?.status !== 'handed_off' ? (
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
