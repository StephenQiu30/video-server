'use client';

import { ShieldCheckIcon } from '@phosphor-icons/react';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import {
  beginProviderAuthorization,
  cancelProviderAuthorization,
  getProviderAuthorization,
} from '@/api/providers';
import { useAuth } from '@/components/auth/auth-provider';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';
import { ApiError, displayError } from '@/lib/request-error';

const POLL_INTERVAL_MS = 2_000;
enum ProviderAuthorizationStatusCode {
  Pending = 'pending',
  SourceAvailable = 'source_available',
  AuthorizationRequired = 'authorization_required',
  PermissionRequired = 'permission_required',
  Expired = 'expired',
  Cancelled = 'cancelled',
  Failed = 'failed',
}

const AUTHORIZATION_STATUS_MESSAGES: Record<
  API.ProviderAuthorizationStatus,
  string | null
> = {
  [ProviderAuthorizationStatusCode.Pending]: null,
  [ProviderAuthorizationStatusCode.SourceAvailable]: null,
  [ProviderAuthorizationStatusCode.AuthorizationRequired]:
    '平台仍要求完成登录或验证',
  [ProviderAuthorizationStatusCode.PermissionRequired]:
    '本机隔离浏览器会话尚未就绪',
  [ProviderAuthorizationStatusCode.Expired]: '授权窗口已超时，请重新发起',
  [ProviderAuthorizationStatusCode.Cancelled]: null,
  [ProviderAuthorizationStatusCode.Failed]: '本机授权失败，请稍后重试',
};

type AuthorizationProvider = Pick<
  API.ProviderListResponse['items'][number],
  'authorization_action' | 'key' | 'display_name'
>;

export function ProviderAuthorizationDialog({
  onAuthorized,
  provider,
}: {
  onAuthorized?: () => void | Promise<void>;
  provider: AuthorizationProvider;
}) {
  const { user } = useAuth();

  if (provider.authorization_action === 'managed_session') {
    return onAuthorized ? (
      <ManagedSessionAction
        onAuthorized={onAuthorized}
        provider={provider.display_name}
      />
    ) : null;
  }

  // Publishing a browser session changes the shared, host-managed Provider
  // source. Keep that operation on the administrator boundary instead of
  // showing a control that a regular user can only discover is forbidden
  // after opening the dialog.
  if (user?.role !== 'admin') return null;
  if (provider.authorization_action !== 'browser_session') return null;
  return (
    <ChromeProviderAuthorizationDialog
      onAuthorized={onAuthorized}
      provider={provider}
    />
  );
}

function ChromeProviderAuthorizationDialog({
  onAuthorized,
  provider,
}: {
  onAuthorized?: () => void | Promise<void>;
  provider: AuthorizationProvider;
}) {
  const [open, setOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const [transaction, setTransaction] =
    useState<API.ProviderAuthorizationResponse | null>(null);
  const [setupRequired, setSetupRequired] = useState(false);
  const [startError, setStartError] = useState('');
  const pollingRef = useRef(false);
  const mountedRef = useRef(false);
  const generationRef = useRef(0);
  const transactionRef = useRef<API.ProviderAuthorizationResponse | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
    };
  }, []);

  useEffect(() => {
    if (
      !open ||
      !transaction ||
      transaction.status !== ProviderAuthorizationStatusCode.Pending ||
      setupRequired ||
      startError
    ) {
      return;
    }

    const poll = async () => {
      if (pollingRef.current) return;
      const generation = generationRef.current;
      const transactionId = transaction.transaction_id;
      pollingRef.current = true;
      try {
        const next = await getProviderAuthorization({
          transaction_id: transactionId,
        });
        if (
          generation !== generationRef.current ||
          transactionId !== transaction.transaction_id
        )
          return;
        transactionRef.current = next;
        setTransaction(next);
        if (next.status === ProviderAuthorizationStatusCode.SourceAvailable) {
          toast.success(`${provider.display_name} 会话已同步，正在验证链接`);
          await onAuthorized?.();
        } else {
          const message = AUTHORIZATION_STATUS_MESSAGES[next.status];
          if (message) toast.error(message);
        }
      } catch (error) {
        const message = displayError(error);
        setStartError(message);
        toast.error(message);
      } finally {
        pollingRef.current = false;
      }
    };

    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [
    onAuthorized,
    open,
    provider.display_name,
    setupRequired,
    startError,
    transaction,
  ]);

  async function startAuthorization() {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    setOpen(true);
    setStarting(true);
    setSetupRequired(false);
    setStartError('');
    transactionRef.current = null;
    setTransaction(null);
    let started: API.ProviderAuthorizationResponse | null = null;
    try {
      started = await beginProviderAuthorization(
        {
          provider_key: provider.key,
        },
        {
          source: 'dedicated_chrome',
        },
      );
      const next = started;
      if (generation !== generationRef.current) {
        // Navigation leaves the durable operation running. An explicit dialog
        // cancellation while this component remains mounted still cancels it.
        if (mountedRef.current) {
          await cancelProviderAuthorization({
            transaction_id: next.transaction_id,
          }).catch(() => undefined);
        }
        return;
      }
      transactionRef.current = next;
      setTransaction(next);
    } catch (error) {
      if (generation !== generationRef.current) return;
      if (started?.status === ProviderAuthorizationStatusCode.Pending) {
        await cancelProviderAuthorization({
          transaction_id: started.transaction_id,
        }).catch(() => undefined);
        transactionRef.current = null;
        setTransaction(null);
      }
      setSetupRequired(
        error instanceof ApiError &&
          error.code === 'provider_configuration_missing',
      );
      setStartError(displayError(error));
      toast.error(displayError(error));
    } finally {
      if (generation === generationRef.current) setStarting(false);
    }
  }

  async function closeAuthorization() {
    const current = transactionRef.current;
    generationRef.current += 1;
    setOpen(false);
    transactionRef.current = null;
    setTransaction(null);
    setSetupRequired(false);
    setStartError('');
    if (current?.status !== ProviderAuthorizationStatusCode.Pending) return;
    try {
      await cancelProviderAuthorization({
        transaction_id: current.transaction_id,
      });
    } catch (error) {
      toast.error(displayError(error));
    }
  }

  return (
    <>
      <Button
        disabled={starting}
        onClick={() => void startAuthorization()}
        size="sm"
        variant="secondary"
      >
        <ShieldCheckIcon aria-hidden data-icon="inline-start" />
        {starting ? '正在打开隔离浏览器…' : '使用隔离浏览器会话'}
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!next) void closeAuthorization();
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>使用隔离浏览器会话</DialogTitle>
            <DialogDescription>
              本机 Access Agent 会打开一个按平台隔离的 Chrome
              会话。登录完成后，会话只保存在当前设备的受控目录中，不会把 Cookie
              上传到服务端。{' '}
              检测成功后，后续解析和下载会自动复用当前设备的受控会话。
            </DialogDescription>
          </DialogHeader>
          {setupRequired ? (
            <SetupRequired />
          ) : startError ? (
            <AuthorizationError message={startError} />
          ) : transaction?.status ===
            ProviderAuthorizationStatusCode.Pending ? (
            <AuthorizationPending provider={provider.display_name} />
          ) : (
            <AuthorizationResult
              provider={provider.display_name}
              status={transaction?.status}
            />
          )}
          <DialogFooter>
            {transaction?.status === ProviderAuthorizationStatusCode.Pending ? (
              <Button
                onClick={() => void closeAuthorization()}
                variant="outline"
              >
                取消授权
              </Button>
            ) : (
              <Button onClick={() => void closeAuthorization()}>关闭</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function ManagedSessionAction({
  onAuthorized,
  provider,
}: {
  onAuthorized?: () => void | Promise<void>;
  provider: string;
}) {
  const [retrying, setRetrying] = useState(false);

  async function retryWithManagedSession() {
    setRetrying(true);
    try {
      await onAuthorized?.();
    } finally {
      setRetrying(false);
    }
  }

  return (
    <Button
      disabled={retrying}
      onClick={() => void retryWithManagedSession()}
      size="sm"
      variant="secondary"
    >
      <ShieldCheckIcon aria-hidden data-icon="inline-start" />
      {retrying ? `正在使用 ${provider} 托管线路…` : '使用托管线路重试'}
    </Button>
  );
}

function AuthorizationPending({ provider }: { provider: string }) {
  return (
    <div aria-busy aria-live="polite" className="flex flex-col gap-4">
      <p className="text-sm leading-6 text-muted-foreground">
        {`正在等待隔离 Chrome 中的 ${provider} 会话。请在新打开的窗口完成登录或验证；不需要复制 Cookie，也不需要重建容器。`}
      </p>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner aria-label="等待平台授权" />
        <span>正在等待本机会话验证…</span>
      </div>
    </div>
  );
}

function AuthorizationResult({
  provider,
  status,
}: {
  provider: string;
  status: API.ProviderAuthorizationStatus | undefined;
}) {
  const messages: Record<API.ProviderAuthorizationStatus, string> = {
    pending: '正在等待平台验证。',
    source_available: `${provider} 会话已同步；系统将通过实际链接继续验证可用性。`,
    authorization_required: '平台仍要求登录或额外验证，请重新发起授权。',
    permission_required:
      '本机隔离浏览器会话不可读取，请检查浏览器权限后重新发起授权。',
    expired: '授权事务已过期，请重新发起授权。',
    cancelled: '授权已取消。',
    failed: '本机授权失败，请稍后重试。',
  };
  return (
    <p aria-live="polite" className="text-sm leading-6 text-muted-foreground">
      {status ? messages[status] : '正在准备本机授权…'}
    </p>
  );
}

function SetupRequired() {
  return (
    <Alert>
      <AlertTitle>本机 Access Agent 尚未安装</AlertTitle>
      <AlertDescription>
        <p>
          请按项目运行手册完成一次本机初始化；初始化后，可以在这里打开隔离浏览器完成平台授权。
        </p>
        <p>
          Agent 必须与 Docker Compose
          运行在同一台设备上；本项目不会通过公共代理或共享账号绕过平台验证。
        </p>
      </AlertDescription>
    </Alert>
  );
}

function AuthorizationError({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
