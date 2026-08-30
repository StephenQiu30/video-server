import { PencilSimple } from '@phosphor-icons/react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemFooter,
  ItemGroup,
  ItemTitle,
} from '@/components/ui/item';
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
  onEdit: (item: API.ManagedUserResponse) => void;
};

export function UserList({ items, currentUserId, onEdit }: UserListProps) {
  function action(item: API.ManagedUserResponse) {
    const self = item.id === currentUserId;
    return (
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
        <PencilSimple />
        管理
      </Button>
    );
  }

  function badges(item: API.ManagedUserResponse) {
    return (
      <span className="flex flex-wrap gap-1.5">
        <Badge variant={item.role === 'admin' ? 'default' : 'neutral'}>
          {item.role === 'admin' ? '管理员' : '普通用户'}
        </Badge>
        <Badge variant={item.is_active ? 'success' : 'neutral'}>
          {item.is_active ? '已启用' : '已停用'}
        </Badge>
      </span>
    );
  }

  return (
    <>
      <div className="hidden overflow-hidden rounded-md md:block">
        <Table className="table-fixed">
          <TableCaption className="sr-only">用户账户列表</TableCaption>
          <TableHeader className="bg-muted/35">
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[24%] px-4 text-xs font-normal text-muted-foreground">
                用户名
              </TableHead>
              <TableHead className="w-[28%] px-4 text-xs font-normal text-muted-foreground">
                邮箱
              </TableHead>
              <TableHead className="w-[23%] px-4 text-xs font-normal text-muted-foreground">
                身份与状态
              </TableHead>
              <TableHead className="w-[15%] px-4 text-xs font-normal text-muted-foreground">
                注册日期
              </TableHead>
              <TableHead className="w-[10%] px-4 text-right text-xs font-normal text-muted-foreground">
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
                <TableCell className="px-4 py-5 text-right">
                  {action(item)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <ItemGroup className="gap-2 md:hidden">
        {items.map((item) => (
          <Item
            className="rounded-md border-0 px-3 py-5 hover:bg-muted/50"
            key={item.id}
            role="listitem"
          >
            <ItemContent className="min-w-0">
              <ItemTitle className="truncate">{item.username}</ItemTitle>
              <ItemDescription className="truncate">
                {item.email}
              </ItemDescription>
            </ItemContent>
            <ItemActions>{action(item)}</ItemActions>
            <ItemFooter>
              {badges(item)}
              <time
                className="text-xs text-muted-foreground"
                dateTime={item.created_at}
              >
                {item.created_at.slice(0, 10)}
              </time>
            </ItemFooter>
          </Item>
        ))}
      </ItemGroup>
    </>
  );
}
