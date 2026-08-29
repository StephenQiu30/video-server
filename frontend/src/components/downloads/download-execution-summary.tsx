import {
  CheckCircle,
  ShieldCheck,
  WarningCircle,
  XCircle,
} from '@phosphor-icons/react';

import {
  Item,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import type { DownloadJob } from '@/types/video';
import { displayStage, executionTitle } from './download-state-model';

export function DownloadExecutionSummary({ job }: { job: DownloadJob }) {
  const complete = job.status === 'succeeded';
  const failed = job.status === 'failed';
  const cancelled = job.status === 'cancelled';

  return (
    <Item className="mt-7 items-start rounded-none px-0 py-0" size="sm">
      <ItemMedia variant="icon">
        {complete ? (
          <ShieldCheck aria-hidden />
        ) : failed ? (
          <WarningCircle aria-hidden />
        ) : cancelled ? (
          <XCircle aria-hidden />
        ) : (
          <CheckCircle aria-hidden />
        )}
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{executionTitle(job)}</ItemTitle>
        <ItemDescription className="line-clamp-none">
          {complete ? (
            <span>{job.file_available ? '持久保存' : '文件已清理'}</span>
          ) : (
            <span>{displayStage(job)}</span>
          )}{' '}
          · 第 {job.attempt} 次执行
        </ItemDescription>
      </ItemContent>
    </Item>
  );
}
