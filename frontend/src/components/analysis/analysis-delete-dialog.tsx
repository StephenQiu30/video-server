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

export default function AnalysisDeleteDialog({
  busy,
  onDelete,
}: {
  busy: boolean;
  onDelete: () => Promise<void>;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button disabled={busy} variant="outline">
          {busy ? <Spinner aria-hidden /> : <Trash aria-hidden />}
          删除分析
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogMedia>
            <Warning aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>删除分析与报告？</AlertDialogTitle>
          <AlertDialogDescription>
            分析记录会立即从页面隐藏，Markdown 与 DOCX
            私有对象随后异步删除。此操作不可撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>保留分析</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onDelete}>
            确认删除
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
