'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import SiteHeader, { BrandLink } from '@/components/site-header';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from '@/components/ui/card';
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { InputGroup, InputGroupAddon } from '@/components/ui/input-group';
import { Separator } from '@/components/ui/separator';

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
    <main className="min-h-screen bg-background" id="main-content">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-5 sm:px-6 sm:py-6">
        <BrandLink />
        <div className="flex flex-1 items-center justify-center py-12 sm:py-16">
          <Card
            aria-labelledby={titleId}
            className="w-full max-w-[440px] gap-0 rounded-xl bg-card py-0 shadow-none ring-1 ring-border"
            role="region"
          >
            <CardHeader className="gap-0 px-6 py-6 sm:px-8 sm:py-7">
              <p className="mb-2 text-sm font-medium text-primary">{eyebrow}</p>
              <h1
                className="text-[32px] font-medium tracking-[-0.03em]"
                id={titleId}
              >
                {title}
              </h1>
              <CardDescription className="mt-2 text-[15px] leading-6">
                {description}
              </CardDescription>
            </CardHeader>
            <Separator />
            <CardContent className="px-6 py-6 sm:px-8 sm:py-7">
              {children}
            </CardContent>
          </Card>
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
      <InputGroup className="h-10 bg-background">
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
        className="bg-muted/70 text-muted-foreground"
        id={id}
        readOnly
        value={value}
      />
      <FieldDescription id={`${id}-help`}>{description}</FieldDescription>
    </Field>
  );
}

export default AppShell;
