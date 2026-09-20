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
import { Spinner } from '@/components/ui/spinner';

type StorageFileDeleteDialogProps = {
  deleting: boolean;
  error: string;
  item: API.StoredFileResponse | null;
  onClose: () => void;
  onConfirm: () => void;
};

export function StorageFileDeleteDialog({
  deleting,
  error,
  item,
  onClose,
  onConfirm,
}: StorageFileDeleteDialogProps) {
  return (
    <AlertDialog
      open={Boolean(item)}
      onOpenChange={(open) => {
        if (!open && !deleting) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="text-destructive">
            <Trash aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>删除文件？</AlertDialogTitle>
          <AlertDialogDescription>
            {item ? `“${item.name}”及其所有持久对象将被永久删除。` : null}
            正在分析的源文件无法删除。
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error ? (
          <Alert variant="destructive">
            <WarningCircle aria-hidden />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <Button
            disabled={deleting || !item}
            onClick={onConfirm}
            variant="destructive"
          >
            {deleting ? (
              <Spinner aria-hidden data-icon="inline-start" />
            ) : (
              <Trash aria-hidden data-icon="inline-start" />
            )}
            {deleting ? '正在删除' : '确认删除'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
