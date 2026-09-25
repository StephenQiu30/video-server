import { CaretDown, PencilSimple, Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
} from '@/components/layout/bulk-delete-selection';
import { DataTable } from '@/components/layout/data-table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

type UserListProps = {
  bulk?: BulkDeleteOptions;
  items: API.ManagedUserResponse[];
  currentUserId: string;
  onDelete: (item: API.ManagedUserResponse) => void;
  onEdit: (item: API.ManagedUserResponse) => void;
};

export function UserList({
  bulk,
  items,
  currentUserId,
  onDelete,
  onEdit,
}: UserListProps) {
  function action(item: API.ManagedUserResponse) {
    const self = item.id === currentUserId;
    return (
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              aria-label={`管理用户 ${item.username}`}
              disabled={self}
              size="sm"
              title={self ? '不能修改或删除当前登录管理员' : '管理用户'}
              type="button"
              variant="ghost"
            >
              <PencilSimple aria-hidden data-icon="inline-start" />
              管理
              <CaretDown aria-hidden data-icon="inline-end" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuGroup>
              <DropdownMenuItem onSelect={() => onEdit(item)}>
                <PencilSimple aria-hidden />
                编辑用户
              </DropdownMenuItem>
              <DropdownMenuItem
                aria-label={`删除用户 ${item.username}`}
                onSelect={() => onDelete(item)}
                variant="destructive"
              >
                <Trash aria-hidden />
                删除用户
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  }

  function badges(item: API.ManagedUserResponse) {
    return (
      <span className="flex flex-wrap gap-1.5">
        <Badge variant={item.role === 'admin' ? 'default' : 'secondary'}>
          {item.role === 'admin' ? '管理员' : '普通用户'}
        </Badge>
        <Badge variant={item.is_active ? 'default' : 'secondary'}>
          {item.is_active ? '已启用' : '已停用'}
        </Badge>
        {(item.role === 'admin' || item.quota.exempt) && (
          <Badge variant="secondary">配额豁免</Badge>
        )}
      </span>
    );
  }

  return (
    <BulkDeleteSelection
      ids={items
        .filter((item) => item.id !== currentUserId)
        .map((item) => item.id)}
      options={bulk}
    >
      <div className="overflow-x-auto rounded-md">
        <DataTable<API.ManagedUserResponse>
          data={items}
          getRowId={(item) => item.id}
          getRowLabel={(item) => item.username}
          caption="用户账户列表"
          className="min-w-[760px] table-fixed"
          columns={[
            {
              id: '用户名',
              header: '用户名',
              className: 'whitespace-normal',
              cell: (item) => (
                <span className="break-all">{item.username}</span>
              ),
            },
            {
              id: '邮箱',
              header: '邮箱',
              cell: (item) => (
                <span className="block truncate" title={item.email}>
                  {item.email}
                </span>
              ),
            },
            {
              id: '身份与状态',
              header: '身份与状态',
              className: 'whitespace-normal',
              cell: (item) => <> {badges(item)} </>,
            },
            {
              id: '注册日期',
              header: '注册日期',
              className: 'tabular-nums whitespace-normal',
              cell: (item) => <> {formatUserDate(item.created_at)} </>,
            },
            {
              id: '操作',
              header: '操作',
              className: 'text-right whitespace-nowrap whitespace-normal',
              cell: (item) => <> {action(item)} </>,
            },
          ]}
        />
      </div>
    </BulkDeleteSelection>
  );
}

const userDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
});

function formatUserDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : userDateFormatter.format(date);
}
