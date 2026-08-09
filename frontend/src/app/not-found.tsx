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
    <main className="content-shell flex min-h-[calc(100svh-72px)] items-center py-14 sm:py-20">
      <Empty className="items-start gap-8 rounded-none border-0 p-0 text-left">
        <EmptyHeader className="max-w-3xl items-start gap-0">
          <p className="eyebrow text-muted-foreground">
            <span className="text-muted-foreground">404</span>
            <span aria-hidden> / 页面状态</span>
          </p>
          <h1 className="mt-6 text-[clamp(3.5rem,8vw,6rem)] font-medium leading-[0.94] tracking-[-0.065em]">
            页面，没有找到。
          </h1>
          <EmptyDescription className="mt-6 max-w-xl text-left text-base leading-7">
            这个地址可能已经移动或失效。返回首页，重新粘贴一个公开视频链接。
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent className="max-w-none items-start">
          <Button asChild size="lg">
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
