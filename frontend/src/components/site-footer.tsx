import Link from 'next/link';

import { cn } from '@/lib/utils';

export function SiteFooter({ className }: { className?: string }) {
  return (
    <footer className={cn('shrink-0 bg-background', className)}>
      <div className="content-shell flex h-16 items-center justify-between gap-6 overflow-hidden py-4 text-xs text-muted-foreground">
        <Link className="focus-ring font-medium text-foreground" href="/">
          帧取
        </Link>
        <span className="truncate whitespace-nowrap">
          解析你有权处理的公开视频
        </span>
      </div>
    </footer>
  );
}

export default SiteFooter;
