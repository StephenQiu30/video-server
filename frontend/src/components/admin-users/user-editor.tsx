import { CheckCircle, SpinnerGap, WarningCircle } from '@phosphor-icons/react';

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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
      <DialogContent>
        <DialogTitle>
          管理用户{editor.user ? `：${editor.user.username}` : ''}
        </DialogTitle>
        <DialogDescription>
          角色和停用状态会在该用户下一次认证请求时立即生效。
        </DialogDescription>
        <div className="mt-6 space-y-6">
          <div className="space-y-2">
            <label htmlFor="edit-role" className="text-sm font-medium">
              账户身份
            </label>
            <Select
              value={editor.role}
              onValueChange={(value) => onRoleChange(value as API.UserRole)}
            >
              <SelectTrigger id="edit-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">管理员</SelectItem>
                <SelectItem value="user">普通用户</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-5 rounded-xl bg-surface px-4 py-3">
            <div>
              <label htmlFor="edit-active" className="text-sm font-medium">
                启用账号
              </label>
              <p className="mt-1 text-xs text-muted-foreground">
                停用后将撤销该账户的 Refresh 会话。
              </p>
            </div>
            <Switch
              id="edit-active"
              checked={editor.active}
              onCheckedChange={onActiveChange}
            />
          </div>
          {editor.error && (
            <Alert variant="destructive">
              <WarningCircle />
              <AlertDescription>{editor.error}</AlertDescription>
            </Alert>
          )}
          <div className="flex justify-end gap-3">
            <DialogClose asChild>
              <Button variant="ghost" disabled={editor.saving}>
                取消
              </Button>
            </DialogClose>
            <Button onClick={onSave} disabled={editor.saving}>
              {editor.saving ? (
                <SpinnerGap className="animate-spin" />
              ) : (
                <CheckCircle />
              )}
              {editor.saving ? '正在保存' : '保存更改'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
