import { Trash } from '@phosphor-icons/react';

import { FeedbackNotice } from '@/components/layout/feedback-notice';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

import type { UserDeletionState } from './model';

type UserDeleteDialogProps = {
  deletion: UserDeletionState;
  onClose: () => void;
  onConfirm: () => void;
};

export function UserDeleteDialog({
  deletion,
  onClose,
  onConfirm,
}: UserDeleteDialogProps) {
  const { user } = deletion;

  return (
    <AlertDialog
      open={Boolean(user)}
      onOpenChange={(open) => {
        if (!open && !deletion.deleting) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia>
            <Trash aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>删除用户？</AlertDialogTitle>
          <AlertDialogDescription>
            {user
              ? `“${user.username}”（${user.email}）的账户将被永久删除。`
              : null}
            登录凭据、角色、配额和会话会一并移除；历史下载文件与任务记录不会自动删除。
          </AlertDialogDescription>
        </AlertDialogHeader>
        {deletion.error ? (
          <FeedbackNotice
            presentation="toast"
            title="操作未完成"
            description={deletion.error}
            tone="error"
          />
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deletion.deleting}>
            取消
          </AlertDialogCancel>
          <Button
            disabled={deletion.deleting || !user}
            onClick={onConfirm}
            variant="destructive"
          >
            {deletion.deleting ? (
              <Spinner aria-hidden data-icon="inline-start" />
            ) : (
              <Trash aria-hidden data-icon="inline-start" />
            )}
            {deletion.deleting ? '正在删除' : '确认删除'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
