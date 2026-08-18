'use client';

import { ArrowRightIcon, WarningCircleIcon } from '@phosphor-icons/react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { type FormEvent, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/components/auth/auth-provider';
import {
  type FieldErrors,
  validateRegistration,
} from '@/components/auth/register-form-model';
import { AuthField, AuthPageFrame } from '@/components/layout/app-shell';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { FieldGroup } from '@/components/ui/field';
import { InputGroupInput } from '@/components/ui/input-group';
import { Spinner } from '@/components/ui/spinner';
import { displayError, register } from '@/services/auth';
import { authRedirect } from '@/utils/authRedirect';

export function RegisterView() {
  const { user, loading, setUser } = useAuth();
  const [redirect, setRedirect] = useState('/');
  const [search, setSearch] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [errorMessage, setErrorMessage] = useState<string>();
  const [submitting, setSubmitting] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const currentSearch = window.location.search;
    const destination = authRedirect(currentSearch);
    setRedirect(destination);
    setSearch(currentSearch);
    if (!loading && user) router.replace(destination);
  }, [loading, router, user]);
  useEffect(() => {
    if (errorMessage) errorRef.current?.focus();
  }, [errorMessage]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const values = {
      username: String(data.get('username') ?? '').trim(),
      email: String(data.get('email') ?? '').trim(),
      password: String(data.get('password') ?? ''),
      confirmPassword: String(data.get('confirmPassword') ?? ''),
    };
    const nextErrors = validateRegistration(values);
    setErrors(nextErrors);
    setErrorMessage(undefined);
    if (Object.keys(nextErrors).length) return;

    setSubmitting(true);
    try {
      const currentUser = await register({
        username: values.username,
        email: values.email,
        password: values.password,
      });
      setUser(currentUser);
      router.replace(redirect);
    } catch (error) {
      setErrorMessage(displayError(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPageFrame
      description="保存下载进度，并在受信任设备上保持登录状态。"
      title="创建账户，保存进度。"
      titleId="register-title"
    >
      <form
        aria-busy={submitting}
        className="space-y-7"
        noValidate
        onSubmit={handleSubmit}
      >
        {errorMessage ? (
          <Alert ref={errorRef} tabIndex={-1} variant="destructive">
            <WarningCircleIcon aria-hidden />
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        ) : null}
        <FieldGroup className="gap-5">
          <AuthField
            error={errors.username}
            idPrefix="register"
            label="用户名"
            name="username"
          >
            <InputGroupInput
              aria-describedby={errors.username ? 'username-error' : undefined}
              aria-invalid={Boolean(errors.username)}
              autoComplete="username"
              className="h-full"
              id="register-username"
              maxLength={32}
              minLength={2}
              name="username"
              placeholder="2–32 个字符"
            />
          </AuthField>
          <AuthField
            error={errors.email}
            idPrefix="register"
            label="邮箱地址"
            name="email"
          >
            <InputGroupInput
              aria-describedby={errors.email ? 'email-error' : undefined}
              aria-invalid={Boolean(errors.email)}
              autoComplete="email"
              className="h-full"
              id="register-email"
              name="email"
              placeholder="name@example.com"
              type="email"
            />
          </AuthField>
          <AuthField
            error={errors.password}
            idPrefix="register"
            label="密码"
            name="password"
          >
            <InputGroupInput
              aria-describedby={errors.password ? 'password-error' : undefined}
              aria-invalid={Boolean(errors.password)}
              autoComplete="new-password"
              className="h-full"
              id="register-password"
              maxLength={128}
              minLength={8}
              name="password"
              placeholder="至少 8 个字符"
              type="password"
            />
          </AuthField>
          <AuthField
            error={errors.confirmPassword}
            idPrefix="register"
            label="确认密码"
            name="confirmPassword"
          >
            <InputGroupInput
              aria-describedby={
                errors.confirmPassword ? 'confirmPassword-error' : undefined
              }
              aria-invalid={Boolean(errors.confirmPassword)}
              autoComplete="new-password"
              className="h-full"
              id="register-confirmPassword"
              name="confirmPassword"
              placeholder="再次输入密码"
              type="password"
            />
          </AuthField>
        </FieldGroup>
        <Button
          className="h-12 w-full text-[15px]"
          disabled={loading || submitting}
          size="lg"
          type="submit"
        >
          {submitting ? (
            <Spinner
              aria-hidden
              className="motion-reduce:animate-none"
              role="presentation"
            />
          ) : null}
          {submitting ? '正在创建…' : '注册并登录'}
          {!submitting ? (
            <ArrowRightIcon aria-hidden className="size-4" />
          ) : null}
        </Button>
      </form>
      <p className="mt-7 text-sm text-muted-foreground">
        已有账号？{' '}
        <Link
          className="focus-ring rounded-sm font-medium text-foreground underline underline-offset-4 decoration-foreground/25 hover:decoration-foreground"
          href={`/user/login${search}`}
        >
          返回登录
        </Link>
      </p>
    </AuthPageFrame>
  );
}
