import { ArrowClockwise, PlugsConnected, Plus } from '@phosphor-icons/react';

import { BackLink } from '@/components/layout/back-link';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

import { ExecutionRoute, ProviderTable } from './ai-provider-list';

type Props = {
  agentAvailable: boolean;
  error: string;
  items: API.AiProviderProfileResponse[];
  loading: boolean;
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
  onActivate,
  onCreate,
  onDelete,
  onEdit,
  onRetry,
}: Props) {
  const active = items.find((item) => item.is_active);
  return (
    <div aria-busy={loading} className="flex flex-col gap-12">
      <div>
        <BackLink className="mb-4" fallbackHref="/" />
        <PageHeader
          action={
            <Button onClick={onCreate}>
              <Plus aria-hidden data-icon="inline-start" />
              新增 AI 服务
            </Button>
          }
          description="默认使用服务端本机 Codex；可在这里新增并启用第三方 API。切换后从下一次分析任务生效，无需修改环境文件。"
          title="AI 服务"
        />
      </div>

      {error ? (
        items.length === 0 ? (
          <PageErrorNotice
            message={error}
            onRetry={onRetry}
            retryLabel="重新加载"
            title="暂时无法读取 AI 服务"
          />
        ) : (
          <FeedbackNotice
            action={
              <Button onClick={onRetry} size="sm" variant="outline">
                <ArrowClockwise aria-hidden data-icon="inline-start" />
                重新加载
              </Button>
            }
            description={error}
            title="操作未完成"
            tone="error"
          />
        )
      ) : null}

      <div>
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
          <Badge variant={agentAvailable ? 'default' : 'destructive'}>
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
                  <Badge variant="secondary">
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
      </div>

      <div>
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2
            className="text-xl font-medium tracking-[-0.025em]"
            id="ai-provider-list"
          >
            Provider 配置
          </h2>
          <p className="text-sm text-muted-foreground">共 {items.length} 条</p>
        </div>
        <div className="flex flex-col gap-1">
          {loading && items.length === 0 ? (
            ['one', 'two', 'three'].map((key) => (
              <div className="py-5" key={key}>
                <Skeleton className="h-14 w-full" />
              </div>
            ))
          ) : items.length > 0 ? (
            <ProviderTable
              items={items}
              onActivate={onActivate}
              onDelete={onDelete}
              onEdit={onEdit}
            />
          ) : error ? null : (
            <PageEmptyNotice
              action={
                <Button onClick={onCreate} type="button">
                  <Plus aria-hidden data-icon="inline-start" />
                  新增第一个 AI 服务
                </Button>
              }
              compact
              description="新增并启用一个 AI Provider 后，分析任务会从这里选择执行线路。"
              icon={<PlugsConnected aria-hidden />}
              title="还没有 AI 服务配置"
            />
          )}
        </div>
      </div>
    </div>
  );
}
