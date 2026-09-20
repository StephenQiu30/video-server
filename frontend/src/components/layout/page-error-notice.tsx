'use client';

import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';
import { cn } from 'cn';

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
  className,
  message,
  onRetry,
  retryLabel = '重试',
  title = '操作未完成',
}: {
  className?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  title?: string;
}) {
  return (
    <Empty
      aria-atomic="true"
      aria-live="assertive"
      className={cn('min-h-80 rounded-none border-0 px-0 py-16', className)}
      role="alert"
    >
      <EmptyMedia className="bg-destructive/10 text-destructive" variant="icon">
        <WarningCircleIcon aria-hidden />
      </EmptyMedia>
      <EmptyHeader className="max-w-md">
        <EmptyTitle className="text-base">{title}</EmptyTitle>
        <EmptyDescription>{message}</EmptyDescription>
      </EmptyHeader>
      {onRetry ? (
        <EmptyContent>
          <Button onClick={onRetry} type="button" variant="outline">
            <ArrowClockwiseIcon aria-hidden data-icon="inline-start" />
            {retryLabel}
          </Button>
        </EmptyContent>
      ) : null}
    </Empty>
  );
}
