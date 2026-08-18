import { MagnifyingGlass } from '@phosphor-icons/react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/button';
import { Field, FieldLabel } from '@/components/ui/field';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from '@/components/ui/input-group';
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
      className="grid items-end gap-4 md:grid-cols-2 lg:grid-cols-[minmax(220px,1fr)_160px_160px_auto]"
    >
      <Field>
        <FieldLabel
          className="text-xs text-muted-foreground"
          htmlFor="user-search"
        >
          搜索用户名或邮箱
        </FieldLabel>
        <InputGroup>
          <InputGroupInput
            className="h-full"
            id="user-search"
            onChange={(event) => onDraftSearch(event.target.value)}
            placeholder="搜索用户名或邮箱"
            value={query.draftSearch}
          />
          <InputGroupAddon>
            <MagnifyingGlass aria-hidden />
          </InputGroupAddon>
        </InputGroup>
      </Field>
      <Field>
        <FieldLabel
          className="text-xs text-muted-foreground"
          htmlFor="user-role-filter"
        >
          账户身份
        </FieldLabel>
        <Select
          value={query.role}
          onValueChange={(value) => onRoleChange(value as RoleFilter)}
        >
          <SelectTrigger className="w-full" id="user-role-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部身份</SelectItem>
            <SelectItem value="admin">管理员</SelectItem>
            <SelectItem value="user">普通用户</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field>
        <FieldLabel
          className="text-xs text-muted-foreground"
          htmlFor="user-active-filter"
        >
          账户状态
        </FieldLabel>
        <Select
          value={query.active}
          onValueChange={(value) => onActiveChange(value as ActiveFilter)}
        >
          <SelectTrigger className="w-full" id="user-active-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="true">已启用</SelectItem>
            <SelectItem value="false">已停用</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Button className="h-10" type="submit">
        <MagnifyingGlass />
        搜索
      </Button>
    </form>
  );
}
