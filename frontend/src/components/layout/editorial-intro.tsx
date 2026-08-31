import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

type EditorialIntroProps = {
  as?: 'h1' | 'h2';
  className?: string;
  description: ReactNode;
  descriptionClassName?: string;
  eyebrow?: string;
  title: ReactNode;
  titleClassName?: string;
  titleId?: string;
};

export function EditorialIntro({
  as = 'h1',
  className,
  description,
  descriptionClassName,
  eyebrow,
  title,
  titleClassName,
  titleId,
}: EditorialIntroProps) {
  const Heading = as;

  return (
    <div className={cn('min-w-0', className)} data-slot="editorial-intro">
      {eyebrow ? (
        <p className="font-mono text-xs font-medium tracking-[0.18em] text-muted-foreground uppercase">
          {eyebrow}
        </p>
      ) : null}
      <Heading
        className={cn(
          as === 'h1'
            ? 'editorial-title'
            : 'text-balance text-[clamp(2.25rem,4vw,3.75rem)] font-medium leading-[0.98] tracking-[-0.055em]',
          eyebrow && 'mt-5',
          titleClassName,
        )}
        id={titleId}
      >
        {title}
      </Heading>
      <p
        className={cn(
          'mt-5 max-w-2xl text-[15px] leading-7 text-muted-foreground',
          descriptionClassName,
        )}
      >
        {description}
      </p>
    </div>
  );
}
