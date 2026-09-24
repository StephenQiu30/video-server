'use client';

import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';
import { cn } from 'cn';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';

export function PageErrorNotice({
  compact = false,
  className,
  message,
  onRetry,
  retryLabel = '重试',
  secondaryAction,
  title = '操作未完成',
  titleAs = 'div',
}: {
  compact?: boolean;
  className?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  secondaryAction?: ReactNode;
  title?: string;
  titleAs?: 'div' | 'h1' | 'h2' | 'h3' | 'h4';
}) {
  return (
    <Empty
      aria-atomic="true"
      aria-live="assertive"
      className={cn(compact && 'flex-none', className)}
      role="alert"
    >
      <EmptyMedia variant="icon">
        <WarningCircleIcon aria-hidden className="text-destructive" />
      </EmptyMedia>
      <EmptyHeader className="max-w-md">
        <EmptyTitle as={titleAs}>{title}</EmptyTitle>
        <EmptyDescription>{message}</EmptyDescription>
      </EmptyHeader>
      {onRetry || secondaryAction ? (
        <EmptyContent className="flex-row flex-wrap justify-center">
          {onRetry ? (
            <Button onClick={onRetry} type="button" variant="outline">
              <ArrowClockwiseIcon aria-hidden data-icon="inline-start" />
              {retryLabel}
            </Button>
          ) : null}
          {secondaryAction}
        </EmptyContent>
      ) : null}
    </Empty>
  );
}
