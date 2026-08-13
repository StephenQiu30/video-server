import { CheckCircle } from '@phosphor-icons/react';

import { BackLink } from '@/components/back-link';
import { PageHeader } from '@/components/page-header';
import { PagePagination } from '@/components/page-pagination';
import { Alert, AlertDescription } from '@/components/ui/alert';

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
    <section aria-busy={result.loading} className="space-y-10">
      <div>
        <BackLink className="mb-4" fallbackHref="/account" />
        <PageHeader
          action={
            <p className="text-xs text-muted-foreground tabular-nums">
              共{' '}
              <strong className="font-semibold text-foreground">
                {result.total}
              </strong>{' '}
              个账户
            </p>
          }
          description="查找账户，并在不离开当前页面的情况下调整角色与启用状态。"
          title="用户管理"
        />
      </div>

      <div className="hairline border-t pt-7">
        <UserFilters
          query={query}
          onDraftSearch={actions.onDraftSearch}
          onSearch={actions.onSearch}
          onRoleChange={actions.onRoleChange}
          onActiveChange={actions.onActiveChange}
        />
      </div>

      {notice && (
        <Alert variant="success">
          <CheckCircle aria-hidden />
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}
      {result.loading && result.items.length === 0 ? (
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

      {!result.error && result.total > 0 && (
        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
          <span>
            显示 {first}–{last}，共 {result.total} 项
          </span>
          <PagePagination
            ariaLabel="用户列表分页"
            className="w-auto justify-end"
            compact
            onPageChange={actions.onPageChange}
            page={result.page}
            pages={pages}
          />
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
