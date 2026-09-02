'use client';

import { Progress as ProgressPrimitive } from 'radix-ui';
import type * as React from 'react';

import { cn } from '@/lib/utils';

function Progress({
  className,
  value = 0,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  const percentage = value ?? 0;
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        'relative h-1.5 w-full overflow-hidden rounded-full bg-muted',
        className,
      )}
      value={value}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="h-full bg-primary transition-transform duration-500 motion-reduce:transition-none"
        style={{ transform: `translateX(-${100 - percentage}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}

export { Progress };
