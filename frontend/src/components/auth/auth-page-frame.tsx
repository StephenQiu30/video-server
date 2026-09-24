'use client';

import type { ReactNode } from 'react';

import { PageHeader } from '@/components/layout/page-header';
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field';
import { InputGroup } from '@/components/ui/input-group';

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
    <div
      className="grid flex-1 gap-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:gap-24"
      data-slot="auth-frame"
    >
      <div className="hidden flex-col justify-center py-20 lg:flex">
        <p className="editorial-title max-w-4xl" data-slot="auth-hero-title">
          把素材，
          <br />
          带回本地。
        </p>
      </div>
      <div className="flex items-center justify-center py-12 lg:justify-start lg:py-20">
        <div className="w-full max-w-[440px]">
          <PageHeader
            description={description}
            title={title}
            titleClassName="text-[clamp(2.5rem,4vw,3rem)]"
            titleId={titleId}
          />
          <div className="pt-8">{children}</div>
        </div>
      </div>
    </div>
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
      <InputGroup className="bg-input">{children}</InputGroup>
      {description ? (
        <FieldDescription id={`${name}-description`}>
          {description}
        </FieldDescription>
      ) : null}
      <FieldError id={`${name}-error`}>{error}</FieldError>
    </Field>
  );
}
