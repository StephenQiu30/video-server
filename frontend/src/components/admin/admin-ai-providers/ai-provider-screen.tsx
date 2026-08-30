import {
  ArrowClockwise,
  CheckCircle,
  Plus,
  WarningCircle,
} from '@phosphor-icons/react';

import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

import { ExecutionRoute, ProviderRow } from './ai-provider-list';

type Props = {
  agentAvailable: boolean;
  error: string;
  items: API.AiProviderProfileResponse[];
  loading: boolean;
  notice: string;
  onActivate: (item: API.AiProviderProfileResponse) => void;
  onCreate: () => void;
  onDelete: (item: API.AiProviderProfileResponse) => void;
  onEdit: (item: API.AiProviderProfileResponse) => void;
  onRetry: () => void;
};

export function AiProviderScreen({
  agentAvailable,
  error,
  items,
  loading,
  notice,
  onActivate,
  onCreate,
  onDelete,
  onEdit,
  onRetry,
}: Props) {
  const active = items.find((item) => item.is_active);
  return (
    <section aria-busy={loading} className="space-y-12">
      <div>
        <BackLink className="mb-4" fallbackHref="/" />
        <PageHeader
          action={
            <Button onClick={onCreate}>
              <Plus aria-hidden />
              新增 Provider
            </Button>
          }
          description="默认使用服务端本机 Codex；可在这里新增并启用第三方 API。切换后从下一次分析任务生效，无需修改环境文件。"
          title="AI 服务"
        />
      </div>

      {notice ? (
        <Alert variant="success">
          <CheckCircle aria-hidden />
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}
      {error ? (
        <Alert variant="destructive">
          <WarningCircle aria-hidden />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            {error}
            <Button onClick={onRetry} size="sm" variant="outline">
              <ArrowClockwise aria-hidden />
              重试
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      <section aria-labelledby="active-ai-route">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              当前执行链路
            </p>
            <h2
              className="mt-1 text-2xl font-medium tracking-[-0.035em]"
              id="active-ai-route"
            >
              Agent 与模型连接状态
            </h2>
          </div>
          <Badge variant={agentAvailable ? 'success' : 'destructive'}>
            {agentAvailable ? 'Agent 在线' : 'Agent 离线'}
          </Badge>
        </div>
        <div className="py-4 sm:py-6">
          {loading && !active ? (
            <Skeleton className="h-20 w-full" />
          ) : active ? (
            <div className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xl font-medium">{active.display_name}</h3>
                  <Badge variant="default">已启用</Badge>
                  <Badge variant="neutral">
                    {active.auth_mode === 'host_login'
                      ? '免 Key'
                      : 'Key 已加密'}
                  </Badge>
                </div>
                <ExecutionRoute active={active} />
              </div>
              <div className="lg:text-right">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Model
                </p>
                <p className="mt-1 font-mono text-sm">{active.model}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              尚未启用 Provider。新增配置后将其设为当前线路。
            </p>
          )}
        </div>
        {!agentAvailable ? (
          <p className="mt-3 text-sm leading-6 text-warning">
            当前未观察到分析 Agent
            状态；配置仍然有效，新的分析任务会先进入可靠队列， 待 Agent
            恢复后继续处理。请检查宿主机分析 Worker、Codex 登录、数据库与
            消息队列。
          </p>
        ) : null}
      </section>

      <section aria-labelledby="ai-provider-list">
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2
            className="text-xl font-medium tracking-[-0.025em]"
            id="ai-provider-list"
          >
            Provider 配置
          </h2>
          <p className="text-sm text-muted-foreground">共 {items.length} 条</p>
        </div>
        <div className="space-y-1">
          {loading && items.length === 0
            ? ['one', 'two', 'three'].map((key) => (
                <div className="py-5" key={key}>
                  <Skeleton className="h-14 w-full" />
                </div>
              ))
            : items.map((item) => (
                <ProviderRow
                  item={item}
                  key={item.key}
                  onActivate={() => onActivate(item)}
                  onDelete={() => onDelete(item)}
                  onEdit={() => onEdit(item)}
                />
              ))}
        </div>
      </section>
    </section>
  );
}
