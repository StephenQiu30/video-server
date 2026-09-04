import type * as React from 'react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export const intakeControlHeightClassName = 'h-16 sm:h-[68px]';

export function IntakeControlRow({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'grid items-stretch gap-2 sm:grid-cols-[minmax(0,1fr)_148px]',
        className,
      )}
      {...props}
    />
  );
}

export function IntakePickerButton({
  className,
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button
      className={cn(
        intakeControlHeightClassName,
        'min-w-0 justify-start px-4 text-left font-normal',
        className,
      )}
      type="button"
      variant="secondary"
      {...props}
    />
  );
}

export function IntakeSubmitButton({
  className,
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button
      className={cn(
        intakeControlHeightClassName,
        'px-6 text-[15px]',
        className,
      )}
      type="submit"
      {...props}
    />
  );
}
