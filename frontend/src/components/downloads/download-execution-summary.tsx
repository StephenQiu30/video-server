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

import {
  DownloadStatusCode,
  displayStage,
  executionTitle,
} from './download-state-model';

export function DownloadExecutionSummary({
  job,
}: {
  job: API.DownloadResponse;
}) {
  const complete = job.status === DownloadStatusCode.Succeeded;
  const failed = job.status === DownloadStatusCode.Failed;
  const cancelled = job.status === DownloadStatusCode.Cancelled;

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
