import { CheckCircle, WarningCircle } from '@phosphor-icons/react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { Switch } from '@/components/ui/switch';

import type { UserEditorState } from './model';

type UserEditorProps = {
  editor: UserEditorState;
  onRoleChange: (value: API.UserRole) => void;
  onActiveChange: (value: boolean) => void;
  onClose: () => void;
  onSave: () => void;
};

export function UserEditor({
  editor,
  onRoleChange,
  onActiveChange,
  onClose,
  onSave,
}: UserEditorProps) {
  return (
    <Dialog
      open={Boolean(editor.user)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="max-h-[calc(100svh-2rem)] gap-0 overflow-y-auto p-0 sm:max-w-[520px]">
        <div className="px-6 pt-6">
          <p className="eyebrow mb-4 text-muted-foreground">账户权限</p>
          <DialogTitle className="text-xl font-medium tracking-[-0.025em]">
            管理用户{editor.user ? `：${editor.user.username}` : ''}
          </DialogTitle>
          <DialogDescription className="mt-2 max-w-md leading-6">
            角色和停用状态会在该用户下一次认证请求时立即生效。
          </DialogDescription>
        </div>
        <form
          aria-busy={editor.saving}
          className="hairline mt-8 border-t px-6 py-6"
          onSubmit={(event) => {
            event.preventDefault();
            if (!editor.saving) onSave();
          }}
        >
          <FieldGroup className="gap-6">
            <Field>
              <FieldLabel htmlFor="edit-role">账户身份</FieldLabel>
              <Select
                disabled={editor.saving}
                value={editor.role}
                onValueChange={(value) => onRoleChange(value as API.UserRole)}
              >
                <SelectTrigger className="w-full" id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">管理员</SelectItem>
                  <SelectItem value="user">普通用户</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field
              className="rounded-md bg-surface px-4 py-4"
              orientation="horizontal"
            >
              <FieldContent>
                <FieldLabel htmlFor="edit-active">启用账号</FieldLabel>
                <FieldDescription className="text-xs">
                  停用后将撤销该账户的 Refresh 会话。
                </FieldDescription>
              </FieldContent>
              <Switch
                checked={editor.active}
                disabled={editor.saving}
                id="edit-active"
                onCheckedChange={onActiveChange}
              />
            </Field>
            {editor.error ? (
              <Alert variant="destructive">
                <WarningCircle aria-hidden />
                <AlertDescription>{editor.error}</AlertDescription>
              </Alert>
            ) : null}
            <div className="hairline -mx-6 -mb-6 mt-2 flex justify-end gap-3 border-t px-6 py-5">
              <DialogClose asChild>
                <Button disabled={editor.saving} type="button" variant="ghost">
                  取消
                </Button>
              </DialogClose>
              <Button disabled={editor.saving || !editor.user} type="submit">
                {editor.saving ? (
                  <Spinner aria-hidden />
                ) : (
                  <CheckCircle aria-hidden />
                )}
                {editor.saving ? '正在保存' : '保存更改'}
              </Button>
            </div>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}
