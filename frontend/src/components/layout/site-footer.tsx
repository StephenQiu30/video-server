import Link from 'next/link';
import { siteConfig } from '@/lib/site';
import { cn } from '@/lib/utils';

export function SiteFooter({ className }: { className?: string }) {
  return (
    <footer className={cn('shrink-0 bg-background', className)}>
      <div className="content-shell flex min-h-16 flex-col justify-between gap-3 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <Link className="focus-ring font-medium text-foreground" href="/">
            帧取 · FrameFetch
          </Link>
          <span>MIT 开源 · 请仅处理已获授权内容</span>
        </div>
        <nav aria-label="项目链接" className="flex items-center gap-4">
          <a
            className="focus-ring hover:text-foreground"
            href={siteConfig.repositoryUrl}
          >
            GitHub
          </a>
          <a
            className="focus-ring hover:text-foreground"
            href={`${siteConfig.repositoryUrl}/tree/main/docs`}
          >
            文档
          </a>
          <a
            className="focus-ring hover:text-foreground"
            href={siteConfig.licenseUrl}
          >
            MIT License
          </a>
        </nav>
      </div>
    </footer>
  );
}

export default SiteFooter;
