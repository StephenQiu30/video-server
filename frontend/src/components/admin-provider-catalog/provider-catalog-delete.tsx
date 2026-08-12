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

import type { CatalogDeleteState } from './model';

type ProviderCatalogDeleteProps = {
  state: CatalogDeleteState;
  onClose: () => void;
  onConfirm: () => void;
};

export function ProviderCatalogDelete({
  state,
  onClose,
  onConfirm,
}: ProviderCatalogDeleteProps) {
  return (
    <AlertDialog
      open={Boolean(state.target)}
      onOpenChange={(open) => {
        if (!open && !state.deleting) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="text-destructive">
            <Trash aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle>
            删除{state.target ? `“${state.target.display_name}”` : '平台'}？
          </AlertDialogTitle>
          <AlertDialogDescription>
            该条目会从平台目录和公开状态页移除。系统下载 Profile
            不会因此被删除。
          </AlertDialogDescription>
        </AlertDialogHeader>
        {state.error ? (
          <Alert variant="destructive">
            <WarningCircle aria-hidden />
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={state.deleting}>取消</AlertDialogCancel>
          <Button
            disabled={state.deleting}
            onClick={onConfirm}
            variant="destructive"
          >
            {state.deleting ? <Spinner aria-hidden /> : <Trash aria-hidden />}
            {state.deleting ? '正在删除' : '确认删除'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
