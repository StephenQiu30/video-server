import { PencilSimple } from '@phosphor-icons/react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

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
        variant="ghost"
        size="sm"
        disabled={self}
        title={self ? '不能修改自己的管理员身份' : '管理用户'}
        aria-label={`管理用户 ${item.username}`}
        onClick={() => onEdit(item)}
      >
        <PencilSimple />
        管理
      </Button>
    );
  }

  function badges(item: API.ManagedUserResponse) {
    return (
      <span className="flex flex-wrap gap-2">
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
    <div className="border-y">
      <table className="hidden w-full table-fixed text-left text-sm md:table">
        <thead className="text-xs text-muted-foreground">
          <tr>
            <th className="w-[24%] px-3 py-3 font-medium">用户名</th>
            <th className="w-[28%] px-3 py-3 font-medium">邮箱</th>
            <th className="w-[23%] px-3 py-3 font-medium">身份与状态</th>
            <th className="w-[15%] px-3 py-3 font-medium">注册日期</th>
            <th className="w-[10%] px-3 py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t">
              <td className="truncate px-3 py-4 font-medium">
                {item.username}
              </td>
              <td className="truncate px-3 py-4 text-muted-foreground">
                {item.email}
              </td>
              <td className="px-3 py-4">{badges(item)}</td>
              <td className="px-3 py-4 text-muted-foreground">
                {item.created_at.slice(0, 10)}
              </td>
              <td className="px-3 py-4 text-right">{action(item)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="divide-y md:hidden">
        {items.map((item) => (
          <article key={item.id} className="space-y-3 py-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="truncate font-medium">{item.username}</h2>
                <p className="mt-1 truncate text-sm text-muted-foreground">
                  {item.email}
                </p>
              </div>
              {action(item)}
            </div>
            <div className="flex items-center justify-between gap-3">
              {badges(item)}
              <span className="text-xs text-muted-foreground">
                {item.created_at.slice(0, 10)}
              </span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
