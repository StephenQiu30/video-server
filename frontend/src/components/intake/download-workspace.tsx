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
import { type ExternalToast, toast } from 'sonner';
import { inspectMedia } from '@/api/inspections';
import { createSourceDiscovery } from '@/api/sourceDiscoveries';
import { ContentIntakeHero } from '@/components/intake/content-intake-hero';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import { intentTitle } from '@/components/intake/intent-status';
import { LinkDownloadForm } from '@/components/intake/link-download-form';
import { MediaUploadForm } from '@/components/intake/media-upload-form';
import {
  hasPublicInput,
  isWeChatArticleInput,
  PUBLIC_INPUT_REQUIRED,
} from '@/components/intake/public-input';
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

type BusyAction = 'inspect' | null;
type StableKey = { payload: string; value: string };
const PARSE_STATUS_TOAST_ID = 'framefetch-parse-status';

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
    openedResultKey,
    setOpenedResultKey,
  } = useIntakeDraft();
  const intent = useDownloadIntent();
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const observedActiveIntentId = useRef<string | null>(null);
  const [authorizationTarget, setAuthorizationTarget] =
    useState<ProviderAuthorizationTarget | null>(null);
  const intentAuthorization =
    intent.snapshot?.status === 'failed' && intent.snapshot.reason_code
      ? providerAuthorizationTarget(url, intent.snapshot.reason_code)
      : null;
  const [urlInvalid, setUrlInvalid] = useState(false);
  useEffect(() => {
    if (!intent.attempt) observedActiveIntentId.current = null;
    else if (
      intent.snapshot &&
      ['queued', 'preparing', 'resolving', 'retry_wait'].includes(
        intent.snapshot.status,
      )
    )
      observedActiveIntentId.current = intent.snapshot.id;
  }, [intent.attempt, intent.snapshot]);
  const showTerminalStatus =
    (!!intent.attempt && intent.attempt.input !== null) ||
    (!!intent.snapshot &&
      observedActiveIntentId.current === intent.snapshot.id);
  const showIntentStatus =
    mode === 'link' &&
    !!intent.attempt &&
    intent.snapshot?.status !== 'handed_off' &&
    ((intent.pending && (!!intent.attempt.input || !!intent.snapshot)) ||
      (showTerminalStatus && (!!intent.error || intent.resultExpired)) ||
      intent.snapshot?.status === 'ready' ||
      (showTerminalStatus &&
        (intent.snapshot?.status === 'failed' ||
          intent.snapshot?.status === 'expired' ||
          intent.snapshot?.status === 'action_required')));
  const inspectionKey = useRef<StableKey | null>(null);
  const discoveryKey = useRef<StableKey | null>(null);
  useEffect(() => {
    const snapshot = intent.snapshot;
    const inspection = intent.inspection;
    if (
      mode !== 'link' ||
      snapshot?.status !== 'ready' ||
      !inspection ||
      intent.resultExpired
    )
      return;
    const key = `${snapshot.id}:${inspection.id}`;
    if (openedResultKey === key) return;
    setOpenedResultKey(key);
    queries.setQueryData(
      privateQueryKey('inspection', inspection.id),
      inspection,
    );
    const target = `/downloads/new?inspectionId=${encodeURIComponent(inspection.id)}&intentId=${encodeURIComponent(snapshot.id)}`;
    markNavigationPush(target);
    router.push(target);
  }, [
    intent.snapshot,
    intent.inspection,
    intent.resultExpired,
    mode,
    openedResultKey,
    queries,
    router,
    setOpenedResultKey,
  ]);
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

  useEffect(() => {
    if (!showIntentStatus) {
      toast.dismiss(PARSE_STATUS_TOAST_ID);
      return;
    }

    const snapshot = intent.snapshot;
    const title = intent.error
      ? '任务状态暂时无法更新'
      : intent.pending && snapshot?.status === 'ready'
        ? '正在更新解析结果'
        : intent.resultExpired
          ? '解析结果已过期'
          : snapshot?.status === 'ready'
            ? '正在加载解析结果'
            : intentTitle(snapshot?.status);
    const description =
      intent.error ??
      (intent.pending && snapshot?.status === 'ready'
        ? '正在更新解析结果，请稍候。'
        : intent.resultExpired
          ? '更新后请重新确认下载规格，无需再次粘贴原链接。'
          : snapshot?.reason_code
            ? localizedErrorMessage(snapshot.reason_code)
            : !snapshot
              ? '正在确认接单，请稍候，无需重复提交。'
              : intent.pending
                ? '任务在后台处理，切换页面不会中断解析。'
                : '本次解析已结束。');
    const action: ExternalToast['action'] =
      intent.resultExpired && !intent.pending ? (
        {
          label: '更新结果',
          onClick: () => {
            void intent.refresh();
          },
        }
      ) : intentAuthorization ? (
        <ProviderAuthorizationDialog
          onAuthorized={() => inspect(intentAuthorization.accessPolicy)}
          provider={{
            authorization_action: intentAuthorization.authorizationAction,
            display_name: intentAuthorization.displayName,
            key: intentAuthorization.key,
          }}
        />
      ) : intent.error ? (
        { label: '恢复任务', onClick: () => void intent.retry() }
      ) : undefined;
    const cancel: ExternalToast['cancel'] =
      snapshot && (intent.pending || snapshot.status === 'action_required') ? (
        <Button
          disabled={intent.cancelling}
          onClick={() => void intent.cancel()}
          size="sm"
          variant="outline"
        >
          {intent.cancelling ? '正在取消…' : '取消解析'}
        </Button>
      ) : undefined;
    const needsAction =
      intent.pending ||
      intent.resultExpired ||
      !!intent.error ||
      snapshot?.status === 'ready' ||
      snapshot?.status === 'action_required';
    const options: ExternalToast = {
      action,
      cancel,
      closeButton: !needsAction,
      description,
      dismissible: !needsAction,
      duration: needsAction ? Number.POSITIVE_INFINITY : 10_000,
      id: PARSE_STATUS_TOAST_ID,
    };
    if (
      intent.error ||
      snapshot?.status === 'failed' ||
      snapshot?.status === 'expired'
    ) {
      toast.error(title, options);
    } else if (intent.resultExpired || snapshot?.status === 'action_required') {
      toast.warning(title, options);
    } else if (intent.pending || snapshot?.status === 'ready') {
      toast.loading(title, options);
    } else {
      toast.info(title, options);
    }
  });

  useEffect(
    () => () => {
      toast.dismiss(PARSE_STATUS_TOAST_ID);
    },
    [],
  );

  function clearLinkResult() {
    if (!intent.pending) intent.clear();
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
        queries.setQueryData(
          privateQueryKey('source-discovery', result.id),
          result,
        );
        const target = `/downloads/new?discoveryId=${encodeURIComponent(result.id)}`;
        markNavigationPush(target);
        router.push(target);
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
        queries.setQueryData(privateQueryKey('inspection', result.id), result);
        const target = `/downloads/new?inspectionId=${encodeURIComponent(result.id)}`;
        markNavigationPush(target);
        router.push(target);
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
            hasResult={false}
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
    </div>
  );
}

function stableKey(ref: RefObject<StableKey | null>, payload: string) {
  if (ref.current?.payload !== payload) {
    ref.current = { payload, value: createIdempotencyKey() };
  }
  return ref.current.value;
}
