'use client';

import { ArrowClockwiseIcon } from '@phosphor-icons/react';

import { FeedbackNotice } from '@/components/layout/feedback-notice';
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
    <FeedbackNotice
      action={
        onRetry ? (
          <Button onClick={onRetry} size="sm" type="button" variant="outline">
            <ArrowClockwiseIcon aria-hidden data-icon="inline-start" />
            重试
          </Button>
        ) : undefined
      }
      className={className}
      description={message}
      title={title}
      tone="error"
    />
  );
}
