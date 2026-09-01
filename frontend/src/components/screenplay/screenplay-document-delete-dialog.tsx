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

export function ScreenplayDocumentDeleteDialog({
  busy,
  compact = false,
  onDelete,
}: {
  busy: boolean;
  compact?: boolean;
  onDelete: () => Promise<void>;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          aria-label={compact ? '删除剧本文档' : undefined}
          disabled={busy}
          size={compact ? 'icon-sm' : 'default'}
          variant="ghost"
        >
          {busy ? <Spinner aria-hidden /> : <Trash aria-hidden />}
          {compact ? <span className="sr-only">删除</span> : '删除文档'}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogMedia>
            <Warning aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>删除剧本文档？</AlertDialogTitle>
          <AlertDialogDescription>
            原始文件、规范化剧本和当前文档记录将永久删除。正在使用该文档的分析需先结束。此操作不可撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>保留文档</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onDelete}>
            确认删除
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
