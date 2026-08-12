import { WarningCircle } from '@phosphor-icons/react/dist/ssr';

import { BackLink } from '@/components/back-link';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
} from '@/components/ui/empty';

export default function MissingDownload() {
  return (
    <main className="content-shell inner-page">
      <BackLink className="mb-4" fallbackHref="/history" />
      <Empty className="min-h-80 items-start justify-start border-0 p-0 pt-8 text-left sm:pt-10">
        <EmptyHeader className="items-start">
          <EmptyMedia className="mb-4" variant="icon">
            <WarningCircle aria-hidden />
          </EmptyMedia>
          <p className="eyebrow mb-3 text-muted-foreground">任务不可用</p>
          <h1 className="text-[36px] font-medium leading-[1.02] tracking-[-0.05em] sm:text-[52px]">
            下载任务不存在
          </h1>
          <EmptyDescription className="mt-2 text-left">
            请从下载历史重新打开任务，或返回首页创建新的下载。
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    </main>
  );
}
