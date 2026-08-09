import { MagnifyingGlass } from '@phosphor-icons/react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { ActiveFilter, RoleFilter, UserQueryState } from './model';

type UserFiltersProps = {
  query: UserQueryState;
  onDraftSearch: (value: string) => void;
  onSearch: (value: string) => void;
  onRoleChange: (value: RoleFilter) => void;
  onActiveChange: (value: ActiveFilter) => void;
};

export function UserFilters({
  query,
  onDraftSearch,
  onSearch,
  onRoleChange,
  onActiveChange,
}: UserFiltersProps) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(query.draftSearch.trim());
  }

  return (
    <form
      onSubmit={submit}
      className="grid gap-3 sm:grid-cols-[minmax(220px,1fr)_160px_160px_auto]"
    >
      <label htmlFor="user-search" className="relative">
        <span className="sr-only">搜索用户名或邮箱</span>
        <MagnifyingGlass
          className="pointer-events-none absolute left-3.5 top-3.5 text-muted-foreground"
          size={17}
        />
        <Input
          id="user-search"
          value={query.draftSearch}
          onChange={(event) => onDraftSearch(event.target.value)}
          placeholder="搜索用户名或邮箱"
          className="pl-10"
        />
      </label>
      <Select
        value={query.role}
        onValueChange={(value) => onRoleChange(value as RoleFilter)}
      >
        <SelectTrigger aria-label="按账户身份筛选" className="h-11">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部身份</SelectItem>
          <SelectItem value="admin">管理员</SelectItem>
          <SelectItem value="user">普通用户</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={query.active}
        onValueChange={(value) => onActiveChange(value as ActiveFilter)}
      >
        <SelectTrigger aria-label="按账户状态筛选" className="h-11">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部状态</SelectItem>
          <SelectItem value="true">已启用</SelectItem>
          <SelectItem value="false">已停用</SelectItem>
        </SelectContent>
      </Select>
      <Button type="submit" className="h-11">
        <MagnifyingGlass />
        搜索
      </Button>
    </form>
  );
}
