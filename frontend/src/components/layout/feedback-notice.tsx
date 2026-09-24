import {
  CheckCircleIcon,
  InfoIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react';
import type { ReactNode } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

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
      <WarningCircleIcon aria-hidden />
    ) : tone === 'success' ? (
      <CheckCircleIcon aria-hidden />
    ) : (
      <InfoIcon aria-hidden />
    );

  return (
    <Alert
      className={className}
      variant={tone === 'error' ? 'destructive' : 'default'}
    >
      {icon}
      {title ? <AlertTitle>{title}</AlertTitle> : null}
      <AlertDescription id={descriptionId} className="min-w-0">
        {description}
        {action ? (
          <div className="mt-3 flex flex-wrap gap-2">{action}</div>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
