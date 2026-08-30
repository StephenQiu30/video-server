import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

type PageHeaderProps = {
  action?: ReactNode;
  className?: string;
  description?: ReactNode;
  title: ReactNode;
  titleClassName?: string;
  titleId?: string;
};

export function PageHeader({
  action,
  className,
  description,
  title,
  titleClassName,
  titleId,
}: PageHeaderProps) {
  return (
    <header
      data-slot="page-header"
      className={cn(
        'flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between sm:gap-8',
        className,
      )}
    >
      <div className="min-w-0 max-w-4xl">
        <h1
          className={cn(
            'text-balance text-[clamp(2.25rem,4vw,3.75rem)] font-medium leading-[0.98] tracking-[-0.055em]',
            titleClassName,
          )}
          id={titleId}
        >
          {title}
        </h1>
        {description ? (
          <p className="mt-2 text-sm leading-6 text-muted-foreground sm:text-base">
            {description}
          </p>
        ) : null}
      </div>
      {action ? (
        <div className="w-full shrink-0 [&>*]:w-full sm:w-auto sm:pt-0.5 sm:[&>*]:w-auto">
          {action}
        </div>
      ) : null}
    </header>
  );
}
