import { ArrowLeft } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <main className="content-shell grid min-h-[70vh] place-items-center py-16 text-center">
      <section>
        <p className="font-mono text-sm text-primary">404</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">
          页面未找到
        </h1>
        <p className="mt-4 text-muted-foreground">
          这个地址已失效，请返回首页重新开始。
        </p>
        <Button asChild className="mt-8">
          <Link href="/">
            <ArrowLeft aria-hidden size={17} />
            返回首页
          </Link>
        </Button>
      </section>
    </main>
  );
}
