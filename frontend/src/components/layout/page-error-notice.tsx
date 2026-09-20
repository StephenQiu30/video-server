'use client';

import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export function PageErrorNotice({
  className,
  message,
  onRetry,
  title = '操作未完成',
}: {
  className?: string;
  message: string;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <Alert className={className} variant="destructive">
      <WarningCircleIcon aria-hidden />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {onRetry ? (
          <Button onClick={onRetry} size="sm" type="button" variant="outline">
            <ArrowClockwiseIcon aria-hidden />
            重试
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
