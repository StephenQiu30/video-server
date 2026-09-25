import {
  ArrowRight,
  Cloud,
  Key,
  PencilSimple,
  Robot,
  TerminalWindow,
  Trash,
} from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
} from '@/components/layout/bulk-delete-selection';
import { type DataColumn, DataTable } from '@/components/layout/data-table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  isDirectApiEngine,
  isLocalCodexProvider,
  providerEngineLabel,
} from './model';

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
          isDirectApiEngine(active.engine)
            ? providerEngineLabel(active.engine)
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

function ProviderRowColumns(
  onActivate: (item: API.AiProviderProfileResponse) => void,
  onDelete: (item: API.AiProviderProfileResponse) => void,
  onEdit: (item: API.AiProviderProfileResponse) => void,
): DataColumn<API.AiProviderProfileResponse>[] {
  return [
    {
      id: '服务',
      header: '服务',
      className: 'whitespace-normal',
      cell: (item) => {
        const localCodex = isLocalCodexProvider(item.key);
        return (
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-medium">{item.display_name}</h3>
              {item.is_active ? (
                <Badge variant="default">当前线路</Badge>
              ) : null}
              {localCodex ? <Badge variant="secondary">系统兜底</Badge> : null}
            </div>
            <p className="truncate text-xs text-muted-foreground">{item.key}</p>
          </div>
        );
      },
    },
    {
      id: '模型与连接',
      header: '模型与连接',
      className: 'w-[32%] whitespace-normal',
      cell: (item) => {
        return (
          <div className="flex min-w-0 flex-col gap-1">
            <span className="truncate font-mono text-xs">{item.model}</span>
            <span className="truncate text-sm text-muted-foreground">
              {item.auth_mode === 'host_login'
                ? '本机账号登录'
                : `${item.base_url} · ${
                    item.credential_configured ? '凭据已配置' : '缺少凭据'
                  }`}
            </span>
          </div>
        );
      },
    },
    {
      id: '执行引擎',
      header: '执行引擎',
      className: 'w-[16%] whitespace-normal',
      cell: (item) => {
        return (
          <Badge variant="secondary">{providerEngineLabel(item.engine)}</Badge>
        );
      },
    },
    {
      id: '操作',
      header: '操作',
      className: 'w-[27%] text-right whitespace-nowrap whitespace-normal',
      cell: (item) => {
        const localCodex = isLocalCodexProvider(item.key);
        return (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {!item.is_active ? (
              <Button
                onClick={() => onActivate(item)}
                size="sm"
                variant="outline"
              >
                启用
              </Button>
            ) : null}
            <Button
              aria-label={`编辑 ${item.display_name}`}
              onClick={() => onEdit(item)}
              size="icon-sm"
              variant="ghost"
            >
              <PencilSimple aria-hidden />
            </Button>
            <Button
              aria-label={`删除 ${item.display_name}`}
              disabled={item.is_active || localCodex}
              onClick={() => onDelete(item)}
              size="icon-sm"
              title={localCodex ? '系统兜底线路不可删除' : undefined}
              variant="ghost"
            >
              <Trash aria-hidden />
            </Button>
          </div>
        );
      },
    },
  ];
}

export function ProviderTable({
  bulk,
  items,
  onActivate,
  onDelete,
  onEdit,
}: {
  bulk?: BulkDeleteOptions;
  items: API.AiProviderProfileResponse[];
  onActivate: (item: API.AiProviderProfileResponse) => void;
  onDelete: (item: API.AiProviderProfileResponse) => void;
  onEdit: (item: API.AiProviderProfileResponse) => void;
}) {
  return (
    <BulkDeleteSelection
      ids={items
        .filter((item) => !item.is_active && !isLocalCodexProvider(item.key))
        .map((item) => item.key)}
      options={bulk}
    >
      <DataTable<API.AiProviderProfileResponse>
        data={items}
        getRowId={(item) => item.key}
        getRowLabel={(item) => item.display_name}
        caption="AI Provider 配置列表"
        className="min-w-[780px] table-fixed"
        columns={ProviderRowColumns(onActivate, onDelete, onEdit)}
      />
    </BulkDeleteSelection>
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
