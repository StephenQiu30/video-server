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
import { requestBrowserProviderSync } from '@/lib/provider-authorization';
import { ApiError, displayError } from '@/lib/request-error';

const POLL_INTERVAL_MS = 2_000;
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
  const [authorizationSource, setAuthorizationSource] =
    useState<API.ProviderAuthorizationSource>('current_chrome');
  const [setupRequired, setSetupRequired] = useState(false);
  const [startError, setStartError] = useState('');
  const pollingRef = useRef(false);
  const generationRef = useRef(0);
  const transactionRef = useRef<API.ProviderAuthorizationResponse | null>(null);

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      const current = transactionRef.current;
      if (current?.status === 'pending') {
        void cancelProviderAuthorization({
          transaction_id: current.transaction_id,
        }).catch(() => undefined);
      }
    };
  }, []);

  useEffect(() => {
    if (
      !open ||
      !transaction ||
      transaction.status !== 'pending' ||
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
        if (next.status === 'source_available') {
          toast.success(`${provider.display_name} 会话已同步，正在验证链接`);
          await onAuthorized?.();
        } else if (next.status === 'authorization_required') {
          toast.error('平台仍要求完成登录或验证');
        } else if (next.status === 'permission_required') {
          toast.error('浏览器连接器尚未完成本机同步');
        } else if (next.status === 'expired') {
          toast.error('授权窗口已超时，请重新发起');
        } else if (next.status === 'failed') {
          toast.error('本机授权失败，请稍后重试');
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

  async function startAuthorization(
    source: API.ProviderAuthorizationSource = 'current_chrome',
  ) {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    setOpen(true);
    setStarting(true);
    setAuthorizationSource(source);
    setSetupRequired(false);
    setStartError('');
    transactionRef.current = null;
    setTransaction(null);
    try {
      if (source === 'current_chrome') {
        await requestBrowserProviderSync(provider.key);
        if (generation !== generationRef.current) return;
      }
      const next = await beginProviderAuthorization(
        {
          provider_key: provider.key,
        },
        {
          source,
        },
      );
      if (generation !== generationRef.current) {
        await cancelProviderAuthorization({
          transaction_id: next.transaction_id,
        }).catch(() => undefined);
        return;
      }
      transactionRef.current = next;
      setTransaction(next);
    } catch (error) {
      if (generation !== generationRef.current) return;
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
    if (current?.status !== 'pending') return;
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
        {starting ? '同步 Chrome…' : '使用当前 Chrome 会话'}
      </Button>
      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!next) void closeAuthorization();
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {authorizationSource === 'current_chrome'
                ? '使用当前 Chrome 会话'
                : '使用隔离浏览器会话'}
            </DialogTitle>
            <DialogDescription>
              {authorizationSource === 'current_chrome'
                ? '浏览器连接器只会通过 Chrome 官方接口读取该平台的必要会话，再交给本机 Access Agent；不会复制整个浏览器配置，也不会把 Cookie 上传到服务端。'
                : '本机 Access Agent 会打开一个按平台隔离的 Chrome 会话。登录完成后，会话只保存在当前设备的受控目录中，不会把 Cookie 上传到服务端。'}{' '}
              检测成功后，后续解析和下载会自动复用当前设备的受控会话。
            </DialogDescription>
          </DialogHeader>
          {setupRequired ? (
            <SetupRequired />
          ) : startError ? (
            <AuthorizationError message={startError} />
          ) : transaction?.status === 'pending' ? (
            <AuthorizationPending
              provider={provider.display_name}
              source={authorizationSource}
            />
          ) : (
            <AuthorizationResult
              onUseDedicated={() => void startAuthorization('dedicated_chrome')}
              provider={provider.display_name}
              status={transaction?.status}
            />
          )}
          <DialogFooter>
            {transaction?.status === 'pending' ? (
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

function AuthorizationPending({
  provider,
  source,
}: {
  provider: string;
  source: API.ProviderAuthorizationSource;
}) {
  return (
    <div aria-busy aria-live="polite" className="flex flex-col gap-4">
      <p className="text-sm leading-6 text-muted-foreground">
        {source === 'current_chrome'
          ? `正在通过浏览器连接器同步当前 Chrome 中的 ${provider} 会话。如果当前 Chrome 尚未登录，请在现有窗口完成登录或验证；连接器会自动提交，不需要复制 Cookie，也不需要重建容器。`
          : `正在等待隔离 Chrome 中的 ${provider} 会话。请在新打开的窗口完成登录或验证；不需要复制 Cookie，也不需要重建容器。`}
      </p>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner aria-label="等待平台授权" />
        <span>正在等待浏览器连接器确认…</span>
      </div>
    </div>
  );
}

function AuthorizationResult({
  onUseDedicated,
  provider,
  status,
}: {
  onUseDedicated: () => void;
  provider: string;
  status: API.ProviderAuthorizationStatus | undefined;
}) {
  const messages: Record<API.ProviderAuthorizationStatus, string> = {
    pending: '正在等待平台验证。',
    source_available: `${provider} 会话已同步；系统将通过实际链接继续验证可用性。`,
    authorization_required: '平台仍要求登录或额外验证，请重新发起授权。',
    permission_required:
      '当前 Chrome 连接器尚未完成本机同步。首次安装连接器后会自动保持会话；无需复制 Cookie，也无需反复授权。如果暂时不安装连接器，可以改用本机隔离浏览器会话。',
    expired: '授权事务已过期，请重新发起授权。',
    cancelled: '授权已取消。',
    failed: '本机授权失败，请稍后重试。',
  };
  return status === 'permission_required' ? (
    <div className="flex flex-col gap-4">
      <p aria-live="polite" className="text-sm leading-6 text-muted-foreground">
        {messages[status]}
      </p>
      <Button onClick={onUseDedicated} variant="outline">
        打开隔离浏览器会话
      </Button>
    </div>
  ) : (
    <p aria-live="polite" className="text-sm leading-6 text-muted-foreground">
      {status ? messages[status] : '正在准备本机授权…'}
    </p>
  );
}

function SetupRequired() {
  return (
    <div className="flex flex-col gap-3 text-sm leading-6 text-muted-foreground">
      <p>
        当前部署尚未安装本机 Access
        Agent。请按项目运行手册完成一次本机初始化；初始化后，
        以后只需在这里点击授权，不再导出或粘贴 Cookie；浏览器连接器会通过 Chrome
        官方接口读取当前 Chrome 中对应平台的会话。
      </p>
      <p>
        Agent 必须与 Docker Compose
        运行在同一台设备上；本项目不会通过公共代理或共享账号绕过平台验证。
      </p>
    </div>
  );
}

function AuthorizationError({ message }: { message: string }) {
  return (
    <p aria-live="assertive" className="text-sm leading-6 text-destructive">
      {message}
    </p>
  );
}
