'use client';

import { Trash } from '@phosphor-icons/react';
import {
  createContext,
  type ReactNode,
  useContext,
  useRef,
  useState,
} from 'react';
import { toast } from 'sonner';
import { BulkSelectionBar } from '@/components/layout/bulk-selection-bar';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { FieldLegend, FieldSet } from '@/components/ui/field';
import { usePageSelection } from '@/hooks/use-page-selection';
import { useRequestScope } from '@/hooks/use-request-scope';
import { displayError } from '@/lib/request-error';

export type BulkDeleteOptions = {
  scope: string;
  disabled: boolean;
  description: string;
  remove: (id: string) => Promise<unknown>;
  onComplete: (deleted: string[]) => void | Promise<void>;
};
const SelectionContext = createContext<null | {
  ids: string[];
  selection: ReturnType<typeof usePageSelection>;
  disabled: boolean;
  toolbar: ReactNode;
}>(null);

/** The caller supplies only the visible, eligible rows and its existing deletion API. */
export function BulkDeleteSelection({
  ids,
  options,
  children,
}: {
  ids: string[];
  options?: BulkDeleteOptions;
  children: ReactNode;
}) {
  if (!options) return children;
  return (
    <SelectionProvider key={options.scope} ids={ids} options={options}>
      {children}
    </SelectionProvider>
  );
}
function SelectionProvider({
  ids,
  options,
  children,
}: {
  ids: string[];
  options: BulkDeleteOptions;
  children: ReactNode;
}) {
  const selection = usePageSelection(options.scope, ids);
  const scope = useRequestScope(options.scope);
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [errors, setErrors] = useState<string[]>([]);
  const disabled = busy || options.disabled;
  async function execute() {
    if (disabled || lock.current || !selection.some) return;
    lock.current = true;
    setBusy(true);
    setProgress(0);
    setErrors([]);
    const request = scope.capture();
    const targets = [...selection.selected];
    setTotal(targets.length);
    const done: string[] = [];
    const failed: string[] = [];
    try {
      for (const id of targets) {
        if (!request.current()) break;
        try {
          await options.remove(id);
          done.push(id);
        } catch (error) {
          failed.push(displayError(error));
        }
        if (request.current()) setProgress(done.length + failed.length);
      }
      if (!request.current()) return;
      selection.remove(done);
      setErrors(failed);
      const message = `已删除 ${done.length} 项，失败 ${failed.length} 项。`;
      if (failed.length) toast.warning(message);
      else toast.success(message);
      await options.onComplete(done);
    } catch (error) {
      if (request.current())
        setErrors((previous) => [...previous, displayError(error)]);
    } finally {
      lock.current = false;
      if (request.current()) setBusy(false);
    }
  }
  const toolbar = (
    <BulkSelectionBar
      count={selection.selected.length}
      busy={disabled}
      onClear={() => selection.toggleAll(false)}
    >
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="outline" disabled={disabled || !selection.some}>
            <Trash data-icon="inline-start" />
            批量删除（{selection.selected.length}）
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>
              删除选中的 {selection.selected.length} 项？
            </AlertDialogTitle>
            <AlertDialogDescription>
              {options.description}此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={disabled || !selection.some}
              onClick={() => void execute()}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </BulkSelectionBar>
  );
  return (
    <SelectionContext.Provider value={{ ids, selection, disabled, toolbar }}>
      {busy ? (
        <p role="status">
          正在删除：{progress} / {total}
        </p>
      ) : null}
      {errors.length ? (
        <FeedbackNotice
          presentation="toast"
          tone="error"
          title="部分项目删除失败，已保留选择"
          description={[...new Set(errors)].join('；')}
        />
      ) : null}
      <FieldSet disabled={disabled} className="min-w-0">
        <FieldLegend className="sr-only">可选记录</FieldLegend>
        {children}
      </FieldSet>
    </SelectionContext.Provider>
  );
}
export function useBulkTableSelection() {
  const context = useContext(SelectionContext);
  if (!context) return undefined;
  return {
    toolbar: context.toolbar,
    ids: context.selection.selected,
    busy: context.disabled,
    toggle: context.selection.toggle,
    eligible: (id: string) => context.ids.includes(id),
  };
}
