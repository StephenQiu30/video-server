import { CheckCircle } from '@phosphor-icons/react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Spinner } from '@/components/ui/spinner';

import { AiProviderFields } from './ai-provider-fields';
import type { AiProviderEditorState } from './model';

type Props = {
  editor: AiProviderEditorState;
  onChange: (values: Partial<AiProviderEditorState>) => void;
  onClose: () => void;
  onSave: () => void;
};

export function AiProviderEditor({ editor, onChange, onClose, onSave }: Props) {
  const creating = editor.mode === 'create';
  return (
    <Dialog
      open={editor.mode !== null}
      onOpenChange={(open) => {
        if (!open && !editor.saving) onClose();
      }}
    >
      <DialogContent className="max-h-[calc(100svh-2rem)] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <p className="mb-4 text-sm font-medium text-primary">AI 分析路由</p>
          <DialogTitle className="text-xl font-medium tracking-[-0.025em]">
            {creating ? '新增 Provider' : `编辑 ${editor.displayName}`}
          </DialogTitle>
          <DialogDescription className="max-w-lg leading-6">
            本机登录模式复用当前用户的 Codex 或 Claude 登录；API Key
            会加密保存，仅在分析任务运行时交给所选适配器，不写入环境文件。
          </DialogDescription>
        </DialogHeader>
        <form
          aria-busy={editor.saving}
          className="grid gap-6"
          onSubmit={(event) => {
            event.preventDefault();
            if (!editor.saving) onSave();
          }}
        >
          <AiProviderFields editor={editor} onChange={onChange} />
          <DialogFooter>
            <Button
              disabled={editor.saving}
              onClick={onClose}
              type="button"
              variant="ghost"
            >
              取消
            </Button>
            <Button disabled={editor.saving} type="submit">
              {editor.saving ? <Spinner aria-hidden /> : <CheckCircle />}
              {editor.saving ? '正在保存' : '保存配置'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
