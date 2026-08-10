'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import { NavigationHistoryProvider } from '@/components/navigation-history';
import { PageHeader } from '@/components/page-header';
import SiteHeader, { BrandLink } from '@/components/site-header';
import { Button } from '@/components/ui/button';
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { InputGroup, InputGroupAddon } from '@/components/ui/input-group';

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = pathname?.startsWith('/user/');

  return (
    <NavigationHistoryProvider currentPath={pathname ?? '/'}>
      {isAuthRoute ? (
        children
      ) : (
        <div className="min-h-screen bg-background text-foreground">
          <Button
            asChild
            className="fixed left-4 top-3 z-[60] h-11 -translate-y-[calc(100%+1rem)] focus-visible:translate-y-0"
          >
            <a href="#main-content">跳到主要内容</a>
          </Button>
          <SiteHeader />
          <div id="main-content" tabIndex={-1}>
            {children}
          </div>
        </div>
      )}
    </NavigationHistoryProvider>
  );
}

type AuthPageFrameProps = {
  children: ReactNode;
  description: string;
  title: string;
  titleId: string;
};

export function AuthPageFrame({
  children,
  description,
  title,
  titleId,
}: AuthPageFrameProps) {
  return (
    <main className="min-h-screen bg-background" id="main-content">
      <div className="page-shell flex min-h-screen flex-col">
        <div className="flex h-20 items-center">
          <BrandLink />
        </div>
        <div className="grid flex-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(420px,0.9fr)]">
          <section
            aria-label="产品介绍"
            className="hidden flex-col justify-between py-20 pr-16 lg:flex xl:pr-24"
          >
            <div>
              <p className="eyebrow text-muted-foreground">公开视频工作流</p>
              <p className="mt-7 max-w-[720px] text-[clamp(3.5rem,6vw,6rem)] font-medium leading-[0.94] tracking-[-0.065em]">
                把视频，
                <br />
                安全带回本地。
              </p>
            </div>
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="size-1.5 rounded-full bg-success" />
              公开链接 · 无 DRM · 安全解析
            </p>
          </section>
          <div className="flex items-center justify-center py-12 lg:justify-start lg:border-l lg:py-20 lg:pl-16 xl:pl-24">
            <section aria-labelledby={titleId} className="w-full max-w-[440px]">
              <PageHeader
                description={description}
                title={title}
                titleClassName="text-[clamp(2.5rem,4vw,3rem)]"
                titleId={titleId}
              />
              <div className="pt-8">{children}</div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}

type AuthFieldProps = {
  children: ReactNode;
  description?: string;
  error?: string;
  icon: ReactNode;
  idPrefix: string;
  label: string;
  name: string;
};

export function AuthField({
  children,
  description,
  error,
  icon,
  idPrefix,
  label,
  name,
}: AuthFieldProps) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={`${idPrefix}-${name}`}>{label}</FieldLabel>
      <InputGroup className="h-11 bg-input">
        {children}
        <InputGroupAddon align="inline-start" className="pl-3">
          {icon}
        </InputGroupAddon>
      </InputGroup>
      {description ? (
        <FieldDescription id={`${name}-description`}>
          {description}
        </FieldDescription>
      ) : null}
      <FieldError id={`${name}-error`}>{error}</FieldError>
    </Field>
  );
}

type ReadOnlyFieldProps = {
  description: string;
  icon: ReactNode;
  id: string;
  label: string;
  value: string;
};

export function ReadOnlyField({
  description,
  icon,
  id,
  label,
  value,
}: ReadOnlyFieldProps) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>
        {icon}
        {label}
      </FieldLabel>
      <Input
        aria-describedby={`${id}-help`}
        aria-readonly="true"
        className="bg-muted text-muted-foreground"
        id={id}
        readOnly
        value={value}
      />
      <FieldDescription id={`${id}-help`}>{description}</FieldDescription>
    </Field>
  );
}

export default AppShell;
