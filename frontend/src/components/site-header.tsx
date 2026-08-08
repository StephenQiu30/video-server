'use client';

import { BookOpenTextIcon, TriangleIcon } from '@phosphor-icons/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navigation = [
  { href: '/', label: '下载' },
  { href: '/history/', label: '历史记录' },
];

export default function SiteHeader() {
  const pathname = usePathname() ?? '/';

  return (
    <header className="border-b bg-background">
      <div className="page-shell flex h-[72px] items-center justify-between">
        <div className="flex items-center gap-9">
          <Link
            aria-label="帧取首页"
            className="flex items-center gap-3 text-xl font-semibold tracking-tight"
            href="/"
          >
            <TriangleIcon aria-hidden className="size-6" weight="fill" />
            <span>帧取</span>
          </Link>
          <nav
            aria-label="主要导航"
            className="hidden items-center gap-8 sm:flex"
          >
            {navigation.map((item) => {
              const active =
                item.href === '/'
                  ? pathname === '/'
                  : pathname.startsWith(item.href.slice(0, -1));
              return (
                <Link
                  className={cn(
                    'relative py-6 text-sm text-muted-foreground transition-colors hover:text-foreground',
                    active && 'font-medium text-foreground',
                  )}
                  href={item.href}
                  key={item.href}
                >
                  {item.label}
                  {active ? (
                    <span className="absolute inset-x-0 -bottom-px h-0.5 bg-foreground" />
                  ) : null}
                </Link>
              );
            })}
          </nav>
        </div>
        <Button asChild className="hidden sm:inline-flex" variant="ghost">
          <a href="/docs" rel="noopener" target="_blank">
            <BookOpenTextIcon data-icon="inline-start" />
            使用说明
          </a>
        </Button>
      </div>
    </header>
  );
}
