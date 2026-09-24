import { type ReactNode, useId } from 'react';
import { Checkbox } from '@/components/ui/checkbox';

export function BulkSelectionBar({
  all,
  some,
  count,
  busy,
  onSelectAll,
  children,
}: {
  all: boolean;
  some: boolean;
  count: number;
  busy: boolean;
  onSelectAll: (checked: boolean) => void;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <fieldset
      className="my-4 flex flex-wrap items-center gap-3"
      aria-label="批量操作"
    >
      <label htmlFor={id} className="flex items-center gap-2 text-sm">
        <Checkbox
          id={id}
          aria-label="全选本页"
          checked={all ? true : some ? 'indeterminate' : false}
          disabled={busy}
          onCheckedChange={(checked) => onSelectAll(checked === true)}
        />
        全选本页
      </label>
      <span className="text-sm text-muted-foreground" aria-live="polite">
        已选 {count} 项
      </span>
      {children}
    </fieldset>
  );
}
