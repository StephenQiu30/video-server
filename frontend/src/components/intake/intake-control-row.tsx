import { cn } from 'cn';
import type * as React from 'react';
import { Button } from '@/components/ui/button';

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
        'h-12 min-w-0 justify-start px-4 text-left font-normal',
        className,
      )}
      size="lg"
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
      className={cn('h-12 px-4', className)}
      size="lg"
      type="submit"
      {...props}
    />
  );
}
