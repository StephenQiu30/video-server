import { CaretDown, PencilSimple, Trash } from '@phosphor-icons/react';

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
  items: API.ManagedUserResponse[];
  currentUserId: string;
  onDelete: (item: API.ManagedUserResponse) => void;
  onEdit: (item: API.ManagedUserResponse) => void;
};

export function UserList({
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
              className="text-muted-foreground hover:text-foreground"
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
    <div className="overflow-x-auto rounded-md">
      <Table className="min-w-[760px] table-fixed">
        <TableCaption className="sr-only">用户账户列表</TableCaption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="px-3 text-xs font-normal text-muted-foreground">
              用户名
            </TableHead>
            <TableHead className="px-3 text-xs font-normal text-muted-foreground">
              邮箱
            </TableHead>
            <TableHead className="px-3 text-xs font-normal text-muted-foreground">
              身份与状态
            </TableHead>
            <TableHead className="px-3 text-xs font-normal text-muted-foreground">
              注册日期
            </TableHead>
            <TableHead className="px-3 text-right text-xs font-normal text-muted-foreground">
              操作
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="max-w-0 truncate px-3 py-2 font-medium">
                {item.username}
              </TableCell>
              <TableCell className="max-w-0 truncate px-3 py-2 text-muted-foreground">
                {item.email}
              </TableCell>
              <TableCell className="px-3 py-2">{badges(item)}</TableCell>
              <TableCell className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                {formatUserDate(item.created_at)}
              </TableCell>
              <TableCell className="px-3 py-2 text-right whitespace-nowrap">
                {action(item)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

const userDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
});

function formatUserDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : userDateFormatter.format(date);
}
