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
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
    <TableRow>
      <TableCell className="max-w-0 px-4 py-5">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium">{item.display_name}</h3>
            {item.is_active ? <Badge variant="default">当前线路</Badge> : null}
            {localCodex ? <Badge variant="secondary">系统兜底</Badge> : null}
          </div>
          <p className="truncate text-xs text-muted-foreground">{item.key}</p>
        </div>
      </TableCell>
      <TableCell className="max-w-0 px-4 py-5">
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
      </TableCell>
      <TableCell className="px-4 py-5">
        <Badge variant="secondary">{providerEngineLabel(item.engine)}</Badge>
      </TableCell>
      <TableCell className="px-4 py-5 text-right whitespace-nowrap">
        <div className="flex flex-wrap items-center justify-end gap-2">
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
      </TableCell>
    </TableRow>
  );
}

export function ProviderTable({
  items,
  onActivate,
  onDelete,
  onEdit,
}: {
  items: API.AiProviderProfileResponse[];
  onActivate: (item: API.AiProviderProfileResponse) => void;
  onDelete: (item: API.AiProviderProfileResponse) => void;
  onEdit: (item: API.AiProviderProfileResponse) => void;
}) {
  return (
    <Table className="min-w-[780px] table-fixed">
      <TableCaption className="sr-only">AI Provider 配置列表</TableCaption>
      <TableHeader className="bg-muted/35">
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-[25%] px-4">服务</TableHead>
          <TableHead className="w-[32%] px-4">模型与连接</TableHead>
          <TableHead className="w-[16%] px-4">执行引擎</TableHead>
          <TableHead className="w-[27%] px-4 text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <ProviderRow
            item={item}
            key={item.key}
            onActivate={() => onActivate(item)}
            onDelete={() => onDelete(item)}
            onEdit={() => onEdit(item)}
          />
        ))}
      </TableBody>
    </Table>
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
