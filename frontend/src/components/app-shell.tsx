'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import SiteHeader, { BrandLink } from '@/components/site-header';

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = pathname?.startsWith('/user/');

  if (isAuthRoute) return <>{children}</>;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        className="focus-ring fixed left-4 top-3 z-[60] -translate-y-20 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white focus:translate-y-0"
        href="#main-content"
      >
        跳到主要内容
      </a>
      <SiteHeader />
      <div id="main-content" tabIndex={-1}>
        {children}
      </div>
    </div>
  );
}

type AuthPageFrameProps = {
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
  titleId: string;
};

export function AuthPageFrame({
  children,
  description,
  eyebrow,
  title,
  titleId,
}: AuthPageFrameProps) {
  return (
    <main className="min-h-screen bg-white" id="main-content">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-5 sm:px-8 sm:py-7">
        <BrandLink />
        <div className="flex flex-1 items-center justify-center py-10 sm:py-16">
          <section aria-labelledby={titleId} className="w-full max-w-[420px]">
            <p className="mb-3 text-sm font-medium text-primary">{eyebrow}</p>
            <h1
              className="text-[32px] font-semibold tracking-[-0.035em] sm:text-[38px]"
              id={titleId}
            >
              {title}
            </h1>
            <p className="mt-3 text-[15px] leading-7 text-muted-foreground">
              {description}
            </p>
            {children}
          </section>
        </div>
      </div>
    </main>
  );
}

type AuthFieldProps = {
  children: ReactNode;
  error?: string;
  icon: ReactNode;
  idPrefix: string;
  label: string;
  name: string;
};

export function AuthField({
  children,
  error,
  icon,
  idPrefix,
  label,
  name,
}: AuthFieldProps) {
  return (
    <div>
      <label
        className="mb-2 block text-sm font-medium"
        htmlFor={`${idPrefix}-${name}`}
      >
        {label}
      </label>
      <div className="relative [&>svg]:pointer-events-none [&>svg]:absolute [&>svg]:left-3.5 [&>svg]:top-3.5 [&>svg]:size-4 [&>svg]:text-muted-foreground">
        {icon}
        {children}
      </div>
      {error ? (
        <p className="mt-1.5 text-sm text-destructive" id={`${name}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export default AppShell;
