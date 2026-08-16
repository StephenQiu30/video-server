'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import BasicLayout from '@/components/basic-layout';
import { NavigationHistoryProvider } from '@/components/navigation-history';
import { PageHeader } from '@/components/page-header';
import { BrandLink } from '@/components/site-header';
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { InputGroup } from '@/components/ui/input-group';

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAuthRoute = pathname?.startsWith('/user/');

  return (
    <NavigationHistoryProvider currentPath={pathname ?? '/'}>
      {isAuthRoute ? children : <BasicLayout>{children}</BasicLayout>}
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
            className="hidden flex-col justify-center py-20 pr-16 lg:flex xl:pr-24"
          >
            <p className="max-w-[720px] text-[clamp(3.5rem,6vw,6rem)] font-medium leading-[0.94] tracking-[-0.065em]">
              把素材，
              <br />
              带回本地。
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
  idPrefix: string;
  label: string;
  name: string;
};

export function AuthField({
  children,
  description,
  error,
  idPrefix,
  label,
  name,
}: AuthFieldProps) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={`${idPrefix}-${name}`}>{label}</FieldLabel>
      <InputGroup className="h-11 bg-input">{children}</InputGroup>
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
  id: string;
  label: string;
  value: string;
};

export function ReadOnlyField({
  description,
  id,
  label,
  value,
}: ReadOnlyFieldProps) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
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
