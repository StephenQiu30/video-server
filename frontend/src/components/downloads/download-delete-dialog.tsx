'use client';

import { Trash, Warning } from '@phosphor-icons/react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

export function DownloadDeleteDialog({
  active,
  busy,
  compact = false,
  onDelete,
}: {
  active: boolean;
  busy: boolean;
  compact?: boolean;
  onDelete: () => Promise<void>;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          aria-label={compact ? '删除下载记录' : undefined}
          className={compact ? '-mr-2' : undefined}
          disabled={busy}
          size={compact ? 'icon-sm' : 'default'}
          variant="ghost"
        >
          {busy ? <Spinner aria-hidden /> : <Trash aria-hidden />}
          {compact ? <span className="sr-only">删除</span> : '删除任务'}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogMedia>
            <Warning aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>删除任务与文件？</AlertDialogTitle>
          <AlertDialogDescription>
            {active ? '当前任务会先被取消。' : ''}
            下载记录、视频文件、本地上传源文件和私有封面将永久删除。此操作不可撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>保留任务</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onDelete}>
            确认删除
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
