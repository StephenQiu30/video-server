'use client';

import type { ReactNode } from 'react';

import SiteFooter from '@/components/layout/site-footer';
import SiteHeader from '@/components/layout/site-header';
import { Button } from '@/components/ui/button';

export function BasicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      <Button
        asChild
        className="fixed left-4 top-3 z-[60] h-11 -translate-y-[calc(100%+1rem)] focus-visible:translate-y-0"
      >
        <a href="#main-content">跳到主要内容</a>
      </Button>
      <SiteHeader />
      <main
        className="content-shell flex flex-1 flex-col"
        id="main-content"
        tabIndex={-1}
      >
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

export default BasicLayout;
