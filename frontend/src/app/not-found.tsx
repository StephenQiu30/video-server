import { ArrowLeft } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
} from '@/components/ui/empty';

export default function NotFound() {
  return (
    <main className="content-shell grid min-h-[70vh] place-items-center py-12 text-center sm:py-16">
      <Empty className="border-0">
        <EmptyHeader>
          <p className="font-mono text-sm text-muted-foreground">404</p>
          <h1 className="mt-2 text-[28px] font-semibold leading-[1.2] tracking-[-0.03em] sm:text-[32px]">
            页面未找到
          </h1>
          <EmptyDescription>
            这个地址已失效，请返回首页重新开始。
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild>
            <Link href="/">
              <ArrowLeft aria-hidden size={17} />
              返回首页
            </Link>
          </Button>
        </EmptyContent>
      </Empty>
    </main>
  );
}
