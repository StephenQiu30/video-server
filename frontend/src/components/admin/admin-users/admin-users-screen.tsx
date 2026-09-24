import { ArrowClockwise } from '@phosphor-icons/react';

import { BackLink } from '@/components/layout/back-link';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { Button } from '@/components/ui/button';

import {
  PAGE_SIZE,
  type UserDeletionState,
  type UserEditorState,
  type UserQueryState,
  type UserQuotaDraft,
  type UserResultState,
} from './model';
import { UserDeleteDialog } from './user-delete-dialog';
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
  onDelete: (user: API.ManagedUserResponse) => void;
  onEditRole: (value: API.UserRole) => void;
  onEditActive: (value: boolean) => void;
  onEditQuota: <K extends keyof UserQuotaDraft>(
    field: K,
    value: UserQuotaDraft[K],
  ) => void;
  onCloseEditor: () => void;
  onSaveEditor: () => void;
  onCloseDelete: () => void;
  onConfirmDelete: () => void;
};

type AdminUsersScreenProps = {
  currentUserId: string;
  query: UserQueryState;
  result: UserResultState;
  editor: UserEditorState;
  deletion: UserDeletionState;
  actions: ScreenActions;
};

export function AdminUsersScreen({
  currentUserId,
  query,
  result,
  editor,
  deletion,
  actions,
}: AdminUsersScreenProps) {
  const pages = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
  const first = result.total === 0 ? 0 : (result.page - 1) * PAGE_SIZE + 1;
  const last = Math.min(result.page * PAGE_SIZE, result.total);

  return (
    <div aria-busy={result.loading} className="flex flex-col gap-10">
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

      <div>
        <UserFilters
          query={query}
          onDraftSearch={actions.onDraftSearch}
          onSearch={actions.onSearch}
          onRoleChange={actions.onRoleChange}
          onActiveChange={actions.onActiveChange}
        />
      </div>

      {result.error && result.items.length > 0 ? (
        <FeedbackNotice
          action={
            <Button onClick={actions.onRetry} size="sm" variant="outline">
              <ArrowClockwise aria-hidden data-icon="inline-start" />
              重新加载
            </Button>
          }
          description={result.error}
          title="用户列表刷新失败"
          tone="error"
        />
      ) : null}
      {result.loading && result.items.length === 0 ? (
        <AdminSkeleton rowsOnly />
      ) : result.items.length === 0 ? (
        result.error ? (
          <UsersLoadError error={result.error} onRetry={actions.onRetry} />
        ) : (
          <EmptyUsers />
        )
      ) : (
        <UserList
          items={result.items}
          currentUserId={currentUserId}
          onDelete={actions.onDelete}
          onEdit={actions.onEdit}
        />
      )}

      {result.total > 0 && (
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
        onQuotaChange={actions.onEditQuota}
        onClose={actions.onCloseEditor}
        onSave={actions.onSaveEditor}
      />
      <UserDeleteDialog
        deletion={deletion}
        onClose={actions.onCloseDelete}
        onConfirm={actions.onConfirmDelete}
      />
    </div>
  );
}
