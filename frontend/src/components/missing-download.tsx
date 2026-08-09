import { ArrowLeft, WarningCircle } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

export default function MissingDownload() {
  return (
    <main className="content-shell grid min-h-[65vh] place-items-center py-16 text-center">
      <section>
        <WarningCircle aria-hidden className="mx-auto text-primary" size={34} />
        <h1 className="mt-5 text-3xl font-semibold tracking-[-0.035em]">
          下载任务不存在
        </h1>
        <p className="mt-3 text-muted-foreground">请从下载历史重新打开任务。</p>
        <Button asChild className="mt-7" variant="outline">
          <Link href="/history/">
            <ArrowLeft aria-hidden size={17} />
            返回下载历史
          </Link>
        </Button>
      </section>
    </main>
  );
}
