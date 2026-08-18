import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export function AiProviderDelete({
  deleting,
  onClose,
  onConfirm,
  target,
}: {
  deleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
  target: API.AiProviderProfileResponse | null;
}) {
  return (
    <AlertDialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open && !deleting) onClose();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>删除 Provider 配置？</AlertDialogTitle>
          <AlertDialogDescription>
            “{target?.display_name}
            ”的加密凭据也会一并删除。当前启用的配置不能删除。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <AlertDialogAction
            disabled={deleting}
            onClick={onConfirm}
            variant="destructive"
          >
            {deleting ? '正在删除' : '确认删除'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
