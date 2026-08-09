import { CaretLeft, CaretRight, CheckCircle } from '@phosphor-icons/react';

import { PageHeader } from '@/components/page-header';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ButtonGroup, ButtonGroupText } from '@/components/ui/button-group';
import { Pagination } from '@/components/ui/pagination';

import {
  PAGE_SIZE,
  type UserEditorState,
  type UserQueryState,
  type UserResultState,
} from './model';
import { UserEditor } from './user-editor';
import { UserFilters } from './user-filters';
import { UserList } from './user-list';
import { AdminSkeleton, EmptyUsers, UsersLoadError } from './user-states';

type ScreenActions = {
  onDraftSearch: (value: string) => void;
  onSearch: (value: string) => void;
  onRoleChange: (value: UserQueryState['role']) => void;
  onActiveChange: (value: UserQueryState['active']) => void;
  onRetry: () => void;
  onPageChange: (value: number) => void;
  onEdit: (user: API.ManagedUserResponse) => void;
  onEditRole: (value: API.UserRole) => void;
  onEditActive: (value: boolean) => void;
  onCloseEditor: () => void;
  onSaveEditor: () => void;
};

type AdminUsersScreenProps = {
  currentUserId: string;
  query: UserQueryState;
  result: UserResultState;
  editor: UserEditorState;
  notice: string;
  actions: ScreenActions;
};

export function AdminUsersScreen({
  currentUserId,
  query,
  result,
  editor,
  notice,
  actions,
}: AdminUsersScreenProps) {
  const pages = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
  const first = result.total === 0 ? 0 : (result.page - 1) * PAGE_SIZE + 1;
  const last = Math.min(result.page * PAGE_SIZE, result.total);

  return (
    <section className="space-y-7">
      <PageHeader
        action={
          <p className="text-sm text-muted-foreground">
            共{' '}
            <strong className="font-semibold text-foreground">
              {result.total}
            </strong>{' '}
            个账户
          </p>
        }
        description="查看账户并调整角色与启用状态。"
        title="用户管理"
      />

      <UserFilters
        query={query}
        onDraftSearch={actions.onDraftSearch}
        onSearch={actions.onSearch}
        onRoleChange={actions.onRoleChange}
        onActiveChange={actions.onActiveChange}
      />

      {notice && (
        <Alert variant="success">
          <CheckCircle aria-hidden />
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}
      {result.loading ? (
        <AdminSkeleton rowsOnly />
      ) : result.error ? (
        <UsersLoadError error={result.error} onRetry={actions.onRetry} />
      ) : result.items.length === 0 ? (
        <EmptyUsers />
      ) : (
        <UserList
          items={result.items}
          currentUserId={currentUserId}
          onEdit={actions.onEdit}
        />
      )}

      {!result.loading && !result.error && result.total > 0 && (
        <footer className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
          <span>
            显示 {first}–{last}，共 {result.total} 项
          </span>
          <Pagination aria-label="用户列表分页" className="w-auto justify-end">
            <ButtonGroup>
              <Button
                aria-label="上一页"
                disabled={result.page <= 1}
                onClick={() => actions.onPageChange(result.page - 1)}
                size="icon-sm"
                type="button"
                variant="outline"
              >
                <CaretLeft aria-hidden />
              </Button>
              <ButtonGroupText
                aria-live="polite"
                className="min-w-20 justify-center bg-background font-normal"
              >
                {result.page} / {pages}
              </ButtonGroupText>
              <Button
                aria-label="下一页"
                disabled={result.page >= pages}
                onClick={() => actions.onPageChange(result.page + 1)}
                size="icon-sm"
                type="button"
                variant="outline"
              >
                <CaretRight aria-hidden />
              </Button>
            </ButtonGroup>
          </Pagination>
        </footer>
      )}

      <UserEditor
        editor={editor}
        onRoleChange={actions.onEditRole}
        onActiveChange={actions.onEditActive}
        onClose={actions.onCloseEditor}
        onSave={actions.onSaveEditor}
      />
    </section>
  );
}
