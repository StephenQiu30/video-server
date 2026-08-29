import {
  ArrowRight,
  Cloud,
  Key,
  PencilSimple,
  Robot,
  TerminalWindow,
  Trash,
} from '@phosphor-icons/react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { isLocalCodexProvider, providerEngineLabel } from './model';

export function ExecutionRoute({
  active,
}: {
  active: API.AiProviderProfileResponse;
}) {
  return (
    <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
      <RouteNode icon={<Robot />} label="本机 Agent" />
      <ArrowRight aria-hidden className="size-4 text-muted-foreground" />
      <RouteNode
        icon={<TerminalWindow />}
        label={
          active.engine === 'deepseek'
            ? 'LangChain · DeepSeek'
            : `${providerEngineLabel(active.engine)} CLI`
        }
      />
      <ArrowRight aria-hidden className="size-4 text-muted-foreground" />
      <RouteNode
        icon={active.auth_mode === 'api_key' ? <Cloud /> : <Key />}
        label={
          active.auth_mode === 'api_key'
            ? active.base_url || 'API 服务'
            : '当前用户登录'
        }
      />
    </div>
  );
}

export function ProviderRow({
  item,
  onActivate,
  onDelete,
  onEdit,
}: {
  item: API.AiProviderProfileResponse;
  onActivate: () => void;
  onDelete: () => void;
  onEdit: () => void;
}) {
  const localCodex = isLocalCodexProvider(item.key);
  return (
    <div className="grid gap-4 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-medium">{item.display_name}</h3>
          {item.is_active ? <Badge variant="success">当前线路</Badge> : null}
          {localCodex ? <Badge variant="neutral">系统兜底</Badge> : null}
          <Badge variant="neutral">{providerEngineLabel(item.engine)}</Badge>
        </div>
        <p className="mt-1 truncate text-sm text-muted-foreground">
          {item.model} ·{' '}
          {item.auth_mode === 'host_login'
            ? '本机账号登录'
            : `${item.base_url} · ${
                item.credential_configured ? '凭据已配置' : '缺少凭据'
              }`}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {!item.is_active ? (
          <Button onClick={onActivate} size="sm" variant="outline">
            启用
          </Button>
        ) : null}
        <Button
          aria-label={`编辑 ${item.display_name}`}
          onClick={onEdit}
          size="icon-sm"
          variant="ghost"
        >
          <PencilSimple aria-hidden />
        </Button>
        <Button
          aria-label={`删除 ${item.display_name}`}
          disabled={item.is_active || localCodex}
          onClick={onDelete}
          size="icon-sm"
          title={localCodex ? '系统兜底线路不可删除' : undefined}
          variant="ghost"
        >
          <Trash aria-hidden />
        </Button>
      </div>
    </div>
  );
}

function RouteNode({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2 rounded-md bg-surface px-3 py-2">
      <span aria-hidden className="shrink-0 text-primary [&>svg]:size-4">
        {icon}
      </span>
      <span className="max-w-64 truncate">{label}</span>
    </span>
  );
}
