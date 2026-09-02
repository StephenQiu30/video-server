import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { Progress } from '@/components/ui/progress';

export function HomeStartup() {
  return (
    <Empty
      asChild
      className="absolute inset-0 z-20 min-h-[60vh] items-start gap-0 rounded-none border-0 bg-background p-0 text-left"
    >
      <section
        aria-atomic="true"
        aria-live="polite"
        data-home-boot
        role="status"
      >
        <EmptyHeader
          className="w-full max-w-md items-start gap-0"
          data-home-boot-copy
        >
          <EmptyDescription className="font-mono text-xs uppercase tracking-[0.2em]">
            FrameFetch / Session
          </EmptyDescription>
          <EmptyTitle className="mt-4 text-xl tracking-[-0.025em]">
            正在确认当前会话
          </EmptyTitle>
          <EmptyDescription className="mt-2 leading-6">
            工作区准备完成后，只呈现与你登录状态匹配的页面。
          </EmptyDescription>
        </EmptyHeader>
        <Progress
          aria-label="正在确认当前会话"
          className="mt-6 h-px max-w-md origin-left rounded-none bg-foreground"
          data-home-boot-line
          value={null}
        />
      </section>
    </Empty>
  );
}
