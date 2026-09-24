import { type ReactNode, useId } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Field,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from '@/components/ui/field';

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
    <FieldSet
      className="my-4 flex-row flex-wrap items-center gap-3"
      aria-label="批量操作"
    >
      <FieldLegend className="sr-only">批量操作</FieldLegend>
      <Field orientation="horizontal" className="w-auto">
        <Checkbox
          id={id}
          aria-label="全选本页"
          checked={all ? true : some ? 'indeterminate' : false}
          disabled={busy}
          onCheckedChange={(checked) => onSelectAll(checked === true)}
        />
        <FieldLabel htmlFor={id}>全选本页</FieldLabel>
      </Field>
      <span className="text-sm text-muted-foreground" aria-live="polite">
        已选 {count} 项
      </span>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </FieldSet>
  );
}
