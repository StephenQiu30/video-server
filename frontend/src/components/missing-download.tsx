import { ArrowLeft, WarningCircle } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
} from '@/components/ui/empty';

export default function MissingDownload() {
  return (
    <main className="content-shell flex min-h-[calc(100svh-144px)] items-center py-12 sm:py-16">
      <Empty className="items-start border-0 p-0 text-left">
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
        <EmptyContent className="mt-4 items-start">
          <Button asChild variant="outline">
            <Link href="/history">
              <ArrowLeft aria-hidden size={17} />
              返回下载历史
            </Link>
          </Button>
        </EmptyContent>
      </Empty>
    </main>
  );
}
