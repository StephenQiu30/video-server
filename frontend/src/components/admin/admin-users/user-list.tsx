import { CaretDown, PencilSimple, Trash } from '@phosphor-icons/react';
import {
  type BulkDeleteOptions,
  BulkDeleteSelection,
  SelectionCell,
  SelectionHead,
} from '@/components/layout/bulk-delete-selection';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

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
        <Table className="min-w-[760px] table-fixed">
          <TableCaption className="sr-only">用户账户列表</TableCaption>
          <TableHeader>
            <TableRow>
              <SelectionHead />
              <TableHead>用户名</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead>身份与状态</TableHead>
              <TableHead>注册日期</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <SelectionCell id={item.id} label={item.username} />
                <TableCell className="max-w-0 truncate">
                  {item.username}
                </TableCell>
                <TableCell className="max-w-0 truncate">{item.email}</TableCell>
                <TableCell>{badges(item)}</TableCell>
                <TableCell className="tabular-nums">
                  {formatUserDate(item.created_at)}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap">
                  {action(item)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
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
