import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

type PageHeaderProps = {
  action?: ReactNode;
  className?: string;
  description?: ReactNode;
  title: ReactNode;
  titleId?: string;
};

export function PageHeader({
  action,
  className,
  description,
  title,
  titleId,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        'flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0 max-w-3xl">
        <h1
          className="text-[28px] font-semibold leading-[1.2] tracking-[-0.03em] sm:text-[32px]"
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
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
