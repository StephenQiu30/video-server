import type * as React from 'react';

import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'focus-ring h-11 w-full min-w-0 rounded-[10px] border border-input bg-white px-3.5 text-[15px] outline-none transition-colors placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-70 aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  );
}

export { Input };
