import { ArrowLeft } from '@phosphor-icons/react/dist/ssr';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';

export default function NotFound() {
  return (
    <main className="content-shell grid min-h-[70vh] place-items-center py-16 text-center">
      <Empty className="border-0">
        <EmptyHeader>
          <p className="font-mono text-sm text-primary">404</p>
          <EmptyTitle className="mt-2 text-4xl font-medium tracking-[-0.04em]">
            页面未找到
          </EmptyTitle>
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
