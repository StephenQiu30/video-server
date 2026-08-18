import { Trash, WarningCircle } from '@phosphor-icons/react';

import { Alert, AlertDescription } from '@/components/ui/alert';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';

type StorageCleanupDialogProps = {
  days: number;
  error: string;
  open: boolean;
  cleaning: boolean;
  onDaysChange: (days: number) => void;
  onClose: () => void;
  onConfirm: () => void;
};

export function StorageCleanupDialog({
  days,
  error,
  open,
  cleaning,
  onDaysChange,
  onClose,
  onConfirm,
}: StorageCleanupDialogProps) {
  return (
    <AlertDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !cleaning) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="text-destructive">
            <Trash aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>清理历史文件？</AlertDialogTitle>
          <AlertDialogDescription>
            将永久删除指定天数前的视频、剧本文档和分析报告。正在执行分析的源文件会被跳过。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-2">
          <Label htmlFor="cleanup-days">清理多少天前的文件</Label>
          <Input
            id="cleanup-days"
            min={1}
            max={3650}
            onChange={(event) => onDaysChange(Number(event.target.value))}
            type="number"
            value={days}
          />
          <p className="text-xs text-muted-foreground">
            默认 30 天，范围 1–3650 天。
          </p>
        </div>
        {error ? (
          <Alert variant="destructive">
            <WarningCircle aria-hidden />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={cleaning}>取消</AlertDialogCancel>
          <Button
            disabled={
              cleaning || !Number.isInteger(days) || days < 1 || days > 3650
            }
            onClick={onConfirm}
            variant="destructive"
          >
            {cleaning ? <Spinner aria-hidden /> : <Trash aria-hidden />}
            {cleaning ? '正在清理' : '确认清理'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
