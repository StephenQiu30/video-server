import {
  CheckCircleIcon,
  InfoIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react';
import { cn } from 'cn';
import type { ReactNode } from 'react';

import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from '@/components/ui/alert';

type FeedbackTone = 'error' | 'info' | 'success';

export function FeedbackNotice({
  action,
  className,
  description,
  descriptionId,
  title,
  tone = 'info',
}: {
  action?: ReactNode;
  className?: string;
  description: ReactNode;
  descriptionId?: string;
  title?: ReactNode;
  tone?: FeedbackTone;
}) {
  const icon =
    tone === 'error' ? (
      <WarningCircleIcon aria-hidden className="text-destructive" />
    ) : tone === 'success' ? (
      <CheckCircleIcon aria-hidden className="text-success" />
    ) : (
      <InfoIcon aria-hidden className="text-muted-foreground" />
    );

  return (
    <Alert
      className={cn(
        'border-0 bg-surface',
        action && 'pr-44 sm:pr-48',
        className,
      )}
      variant={tone === 'error' ? 'destructive' : 'default'}
    >
      {icon}
      <div className="min-w-0">
        {title ? <AlertTitle>{title}</AlertTitle> : null}
        <AlertDescription id={descriptionId}>{description}</AlertDescription>
      </div>
      {action ? (
        <AlertAction className="top-1/2 right-4 -translate-y-1/2 sm:right-5">
          {action}
        </AlertAction>
      ) : null}
    </Alert>
  );
}
