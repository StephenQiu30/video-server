'use client';

import { InfoIcon } from '@phosphor-icons/react';
import { cn } from 'cn';
import type { ReactNode } from 'react';

import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';

export function PageEmptyNotice({
  action,
  className,
  compact = false,
  description,
  eyebrow,
  icon,
  title,
  titleAs = 'h2',
  titleClassName,
}: {
  action?: ReactNode;
  className?: string;
  compact?: boolean;
  description: ReactNode;
  eyebrow?: ReactNode;
  icon?: ReactNode;
  title: ReactNode;
  titleAs?: 'div' | 'h1' | 'h2' | 'h3' | 'h4';
  titleClassName?: string;
}) {
  return (
    <Empty className={cn(compact && 'flex-none', className)}>
      <EmptyMedia variant="icon">{icon ?? <InfoIcon aria-hidden />}</EmptyMedia>
      <EmptyHeader className="max-w-md">
        {eyebrow ? (
          <p className="font-mono text-sm text-muted-foreground">{eyebrow}</p>
        ) : null}
        <EmptyTitle as={titleAs} className={titleClassName}>
          {title}
        </EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      {action ? (
        <EmptyContent className="flex-row flex-wrap justify-center">
          {action}
        </EmptyContent>
      ) : null}
    </Empty>
  );
}
