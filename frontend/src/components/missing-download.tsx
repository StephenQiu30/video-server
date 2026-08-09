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
    <main className="content-shell grid min-h-[70vh] place-items-center py-12 text-center sm:py-16">
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <WarningCircle aria-hidden />
          </EmptyMedia>
          <h1 className="text-[28px] font-semibold leading-[1.2] tracking-[-0.03em] sm:text-[32px]">
            下载任务不存在
          </h1>
          <EmptyDescription>请从下载历史重新打开任务。</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild variant="outline">
            <Link href="/history/">
              <ArrowLeft aria-hidden size={17} />
              返回下载历史
            </Link>
          </Button>
        </EmptyContent>
      </Empty>
    </main>
  );
}
