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
      className={cn('border-0 bg-surface', className)}
      variant={tone === 'error' ? 'destructive' : 'default'}
    >
      {icon}
      {title ? <AlertTitle>{title}</AlertTitle> : null}
      <AlertDescription id={descriptionId}>{description}</AlertDescription>
      {action ? <AlertAction>{action}</AlertAction> : null}
    </Alert>
  );
}
