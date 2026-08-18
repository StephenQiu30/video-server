import { BackLink } from '@/components/layout/back-link';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
} from '@/components/ui/empty';

export default function NotFound() {
  return (
    <div className="flex min-h-[calc(100svh-9rem)] items-center py-14 sm:py-20">
      <Empty className="items-start gap-8 rounded-none border-0 p-0 text-left">
        <EmptyHeader className="max-w-3xl items-start gap-0">
          <p className="font-mono text-sm text-muted-foreground">404</p>
          <h1 className="mt-6 text-[clamp(3.5rem,8vw,6rem)] font-medium leading-[0.94] tracking-[-0.065em]">
            页面，没有找到。
          </h1>
          <EmptyDescription className="mt-6 max-w-xl text-left text-base leading-7">
            这个地址可能已经移动或失效。返回上一步，或回到首页重新粘贴一个公开视频链接。
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent className="max-w-none items-start">
          <BackLink className="ml-0" fallbackHref="/" />
        </EmptyContent>
      </Empty>
    </div>
  );
}
