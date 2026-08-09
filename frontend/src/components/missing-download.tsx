import { ArrowLeft, WarningCircle } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';

export default function MissingDownload() {
  return (
    <main className="content-shell grid min-h-[65vh] place-items-center py-16 text-center">
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <WarningCircle aria-hidden />
          </EmptyMedia>
          <EmptyTitle className="text-3xl font-medium tracking-[-0.035em]">
            下载任务不存在
          </EmptyTitle>
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
