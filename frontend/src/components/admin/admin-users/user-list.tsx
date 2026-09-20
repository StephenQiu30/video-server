import { PencilSimple, Trash } from '@phosphor-icons/react';

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
      <span className="flex justify-end gap-1">
        <Button
          className="text-muted-foreground hover:text-foreground"
          variant="ghost"
          size="sm"
          disabled={self}
          title={self ? '不能修改自己的管理员身份' : '管理用户'}
          aria-label={`管理用户 ${item.username}`}
          onClick={() => onEdit(item)}
          type="button"
        >
          <PencilSimple data-icon="inline-start" />
          管理
        </Button>
        <Button
          aria-label={`删除用户 ${item.username}`}
          className="text-destructive hover:text-destructive"
          disabled={self}
          onClick={() => onDelete(item)}
          size="icon-lg"
          title={self ? '不能删除当前登录管理员' : '删除用户'}
          type="button"
          variant="ghost"
        >
          <Trash aria-hidden />
        </Button>
      </span>
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
        <TableHeader className="bg-muted/35">
          <TableRow className="hover:bg-transparent">
            <TableHead className="px-4 text-xs font-normal text-muted-foreground">
              用户名
            </TableHead>
            <TableHead className="px-4 text-xs font-normal text-muted-foreground">
              邮箱
            </TableHead>
            <TableHead className="px-4 text-xs font-normal text-muted-foreground">
              身份与状态
            </TableHead>
            <TableHead className="px-4 text-xs font-normal text-muted-foreground">
              注册日期
            </TableHead>
            <TableHead className="px-4 text-right text-xs font-normal text-muted-foreground">
              操作
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="max-w-0 truncate px-4 py-5 font-medium">
                {item.username}
              </TableCell>
              <TableCell className="max-w-0 truncate px-4 py-5 text-muted-foreground">
                {item.email}
              </TableCell>
              <TableCell className="px-4 py-5">{badges(item)}</TableCell>
              <TableCell className="px-4 py-5 text-xs text-muted-foreground tabular-nums">
                {item.created_at.slice(0, 10)}
              </TableCell>
              <TableCell className="px-4 py-5 text-right whitespace-nowrap">
                {action(item)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
